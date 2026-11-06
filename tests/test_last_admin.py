import os

import pytest

from api.auth import login
from api.users import get_profile, get_user_as_admin, list_users_as_admin, update_user_as_admin
from tests.assertions import assert_api_error


@pytest.fixture
def isolated_admin():
    """Opt-in endpoint for a disposable API prepared with one active admin."""
    url = os.getenv("ISOLATED_ADMIN_API_URL")
    if not url:
        pytest.skip("Set ISOLATED_ADMIN_API_URL/EMAIL/PASSWORD for a disposable API with one active admin")
    email = os.getenv("ISOLATED_ADMIN_EMAIL")
    password = os.getenv("ISOLATED_ADMIN_PASSWORD")
    if not email or not password:
        pytest.fail("Set ISOLATED_ADMIN_EMAIL and ISOLATED_ADMIN_PASSWORD", pytrace=False)
    url = url.rstrip("/")
    reuse_ci_stand = (
        os.getenv("ISOLATED_ADMIN_REUSE_CI_STAND") == "1"
        and os.getenv("GITHUB_ACTIONS") == "true"
        and os.getenv("RUNNER_ENVIRONMENT") == "github-hosted"
        and os.getenv("SUITE") == "full"
    )
    main_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1").rstrip("/")
    assert reuse_ci_stand or url != main_url, "Use a separate disposable API outside full CI"
    response = login(url, {"email": email, "password": password})
    assert response.status_code == 200, "Isolated admin login failed"
    token = response.json()["access_token"]
    profile = get_profile(url, token)
    assert profile.status_code == 200, profile.text
    admins = list_users_as_admin(url, token, {"role": "admin", "is_active": True})
    assert admins.status_code == 200, admins.text
    assert admins.json()["total"] == 1, "Disposable API must already contain exactly one active admin"
    assert [user["id"] for user in admins.json()["items"]] == [profile.json()["id"]]
    return {"url": url, "token": token, "user": profile.json()}


@pytest.mark.isolated_admin
@pytest.mark.parametrize("change", [{"role": "user"}, {"is_active": False}, {"role": "user", "is_active": False}],
                         ids=["demote", "disable", "demote_and_disable"])
def test_last_active_admin_cannot_be_removed(isolated_admin, change):
    url, token, user = isolated_admin["url"], isolated_admin["token"], isolated_admin["user"]
    response = update_user_as_admin(url, token, user["id"], change)
    assert_api_error(response, status=409, code="LAST_ACTIVE_ADMIN")
    saved = get_user_as_admin(url, token, user["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == user
    admins = list_users_as_admin(url, token, {"role": "admin", "is_active": True})
    assert admins.status_code == 200, admins.text
    assert admins.json()["total"] == 1
    assert [item["id"] for item in admins.json()["items"]] == [user["id"]]
