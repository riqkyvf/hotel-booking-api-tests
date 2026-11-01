from uuid import uuid4

import pytest

from helpers.auth import login, register
from helpers.users import update_user_as_admin


@pytest.fixture
def base_url():
    return "http://localhost:8000/api/v1"


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

    return user_data.copy()


@pytest.fixture
def registered_login_data(registered_user):
    return {
        "email": registered_user["email"],
        "password": registered_user["password"],
    }


@pytest.fixture
def admin_access_token(base_url):
    response = login(
        base_url,
        {
            "email": "admin@example.com",
            "password": "HotelDemo123!",
        },
    )

    assert response.status_code == 200, response.text

    return response.json()["access_token"]


@pytest.fixture
def disabled_user(base_url, user_data, admin_access_token):
    register_response = register(base_url, user_data)

    assert register_response.status_code == 201, register_response.text

    user_id = register_response.json()["id"]

    update_response = update_user_as_admin(
        base_url,
        admin_access_token,
        user_id,
        {"is_active": False},
    )

    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["id"] == user_id
    assert update_response.json()["is_active"] is False

    return user_data
