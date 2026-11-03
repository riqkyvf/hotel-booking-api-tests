import os
from pathlib import Path
from uuid import uuid4

import pytest
from dotenv import load_dotenv

from api.auth import login, register
from api.users import update_user_as_admin


load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


@pytest.fixture(scope="session")
def base_url():
    url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1").strip().rstrip("/")
    if not url:
        pytest.fail("API_BASE_URL must not be empty", pytrace=False)
    return url


@pytest.fixture
def user_data():
    return {
        "email": f"user_{uuid4().hex}@example.com",
        "password": "password12345",
        "name": "Evgeniy",
    }


@pytest.fixture
def login_data(user_data):
    return {
        "email": user_data["email"],
        "password": user_data["password"],
    }


@pytest.fixture
def email_254():
    local_part = uuid4().hex * 2
    domain = ".".join(["a" * 63, "b" * 63, "c" * 61])
    return f"{local_part}@{domain}"


@pytest.fixture
def registered_user(base_url, user_data):
    response = register(base_url, user_data)

    assert response.status_code == 201, response.text

    return {"payload": user_data.copy(), "user": response.json()}


@pytest.fixture
def registered_login_data(registered_user):
    return {
        "email": registered_user["payload"]["email"],
        "password": registered_user["payload"]["password"],
    }


@pytest.fixture
def admin_access_token(base_url):
    email = os.getenv("API_ADMIN_EMAIL")
    password = os.getenv("API_ADMIN_PASSWORD")
    if not email or not password:
        pytest.fail(
            "Set API_ADMIN_EMAIL and API_ADMIN_PASSWORD in the environment or .env "
            "for administrative scenarios",
            pytrace=False,
        )

    response = login(
        base_url,
        {
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200, response.text

    return response.json()["access_token"]


@pytest.fixture
def disabled_user(base_url, registered_user, admin_access_token):
    user_id = registered_user["user"]["id"]

    update_response = update_user_as_admin(
        base_url,
        admin_access_token,
        user_id,
        {"is_active": False},
    )

    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["id"] == user_id
    assert update_response.json()["is_active"] is False

    return registered_user["payload"].copy()
