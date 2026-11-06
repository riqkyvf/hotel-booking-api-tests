"""Run last-admin checks on a disposable local or GitHub Actions stand."""
import argparse
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from urllib.parse import urlsplit
from uuid import uuid4

import requests

ROOT = Path(__file__).resolve().parents[1]


def docker(*args):
    result = subprocess.run(["docker", *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"Docker step failed: {args[0]} (details suppressed to avoid exposing generated credentials)")
    return result.stdout.strip()


def run_checks(url, email, password, *, reuse_ci_stand=False):
    from api.auth import login
    from api.users import get_profile, list_users_as_admin, update_user_as_admin

    logged_in = login(url, {"email": email, "password": password})
    assert logged_in.status_code == 200, "Disposable admin login failed"
    token = logged_in.json()["access_token"]
    profile = get_profile(url, token)
    assert profile.status_code == 200
    admin_id = profile.json()["id"]
    admins = list_users_as_admin(url, token, {"role": "admin", "is_active": True, "limit": 100})
    assert admins.status_code == 200
    page = admins.json()
    assert page["total"] == len(page["items"]), "Expected all active admins on one page"
    assert any(user["id"] == admin_id for user in page["items"]), "Runner admin is missing from the active list"
    for user in page["items"]:
        if user["id"] != admin_id:
            response = update_user_as_admin(url, token, user["id"], {"role": "user"})
            assert response.status_code == 200, f"Admin setup returned HTTP {response.status_code}"

    test_env = {**os.environ, "ISOLATED_ADMIN_API_URL": url,
                "ISOLATED_ADMIN_EMAIL": email, "ISOLATED_ADMIN_PASSWORD": password}
    command = [sys.executable, "-m", "pytest", "-m", "isolated_admin", "-q", "--tb=short"]
    if reuse_ci_stand:
        test_env["ISOLATED_ADMIN_REUSE_CI_STAND"] = "1"
        command += ["--junitxml=artifacts/junit-last-admin.xml", "--alluredir=artifacts/allure-results",
                    "--allure-no-capture"]
    else:
        command += ["--junitxml=junit-last-admin-isolated.xml"]
    return subprocess.run(command, cwd=ROOT, env=test_env).returncode


def run_on_ci_stand():
    if (os.getenv("GITHUB_ACTIONS") != "true" or os.getenv("RUNNER_ENVIRONMENT") != "github-hosted"
            or os.getenv("SUITE") != "full"):
        raise RuntimeError("Reusing a stand is only supported in the full run on a GitHub-hosted runner")
    url = os.environ["API_BASE_URL"].rstrip("/")
    endpoint = urlsplit(url)
    if (endpoint.scheme != "http" or endpoint.hostname != "127.0.0.1" or endpoint.port is None
            or endpoint.path != "/api/v1" or endpoint.username or endpoint.password or endpoint.query
            or endpoint.fragment):
        raise RuntimeError("Expected the disposable API on the runner loopback interface")
    return run_checks(url, os.environ["API_ADMIN_EMAIL"], os.environ["API_ADMIN_PASSWORD"], reuse_ci_stand=True)


def run_on_local_stand():
    prefix = f"codex-last-admin-{uuid4().hex[:12]}"
    network, db, api = prefix, f"{prefix}-db", f"{prefix}-api"
    password = secrets.token_hex(24)
    jwt_secret = secrets.token_hex(32)
    created_network = False
    created_containers = []
    try:
        docker("network", "create", network)
        created_network = True
        docker("run", "-d", "--rm", "--name", db, "--network", network,
               "--tmpfs", "/var/lib/postgresql/data", "-e", "POSTGRES_DB=hotel",
               "-e", "POSTGRES_USER=hotel", "-e", f"POSTGRES_PASSWORD={password}", "postgres:17-alpine")
        created_containers.append(db)
        for _ in range(60):
            ready = subprocess.run(["docker", "exec", db, "pg_isready", "-U", "hotel", "-d", "hotel"], capture_output=True)
            if ready.returncode == 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError("Disposable database did not become ready")
        env_args = ["-e", f"DATABASE_URL=postgresql+psycopg://hotel:{password}@{db}:5432/hotel",
                    "-e", f"JWT_SECRET={jwt_secret}", "-e", f"SEED_PASSWORD={password}"]
        docker("run", "--rm", "--network", network, *env_args, "hotel-booking-api",
               "sh", "-c", "alembic upgrade head && python -m app.scripts.seed")
        docker("run", "-d", "--rm", "--name", api, "--network", network,
               "-p", "127.0.0.1::8000", *env_args, "hotel-booking-api")
        created_containers.append(api)
        port = docker("port", api, "8000/tcp").split(":")[-1]
        url = f"http://127.0.0.1:{port}/api/v1"
        for _ in range(60):
            try:
                if requests.get(f"{url}/health/ready", timeout=2).status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(1)
        else:
            raise RuntimeError("Disposable API did not become ready")
        print("Disposable API ready; configuring its seed admins only.", flush=True)
        return run_checks(url, "admin@example.com", password)
    finally:
        for name in reversed(created_containers):
            subprocess.run(["docker", "rm", "-f", name], capture_output=True)
        if created_network:
            subprocess.run(["docker", "network", "rm", network], capture_output=True)
        print("Disposable containers and network cleanup requested.", flush=True)


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse-ci-stand", action="store_true", help="Reuse the disposable full CI stand")
    args = parser.parse_args()
    raise SystemExit(run_on_ci_stand() if args.reuse_ci_stand else run_on_local_stand())
