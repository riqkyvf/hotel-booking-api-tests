import allure
import pytest

from api.auth import login, register
from api.users import get_profile, update_user_as_admin
from data.auth import ASCII_EMAIL_DOMAINS, VALID_ASCII_PASSWORD_CASES


@pytest.mark.smoke
@allure.title("Зарегистрированный пользователь может войти и открыть профиль")
def test_registered_user_can_login_and_get_profile(base_url, registered_user):
    with allure.step("Войти с данными зарегистрированного пользователя"):
        login_response = login(
            base_url,
            {
                "email": registered_user["payload"]["email"],
                "password": registered_user["payload"]["password"],
            },
        )

        assert login_response.status_code == 200, login_response.text

        access_token = login_response.json()["access_token"]

        assert isinstance(access_token, str)
        assert access_token

    with allure.step("Прочитать и проверить собственный профиль"):
        profile_response = get_profile(base_url, access_token)

        assert profile_response.status_code == 200, profile_response.text

        user = profile_response.json()

        assert user["id"] == registered_user["user"]["id"]
        assert user["email"] == registered_user["payload"]["email"]
        assert user["name"] == registered_user["payload"]["name"]
        assert user["phone"] is None
        assert user["role"] == "user"
        assert user["is_active"] is True
        assert "password" not in user
        assert "password_hash" not in user


def test_duplicate_registration_does_not_change_user(base_url, registered_user):
    duplicate_data = registered_user["payload"].copy()
    duplicate_data["name"] = "Changed Name"
    duplicate_data["password"] = "ChangedPassword123!"

    register_response = register(base_url, duplicate_data)

    assert register_response.status_code == 409, register_response.text
    assert register_response.json()["error"]["code"] == "EMAIL_EXISTS"

    login_response = login(
        base_url,
        {
            "email": registered_user["payload"]["email"],
            "password": registered_user["payload"]["password"],
        },
    )

    assert login_response.status_code == 200, login_response.text

    access_token = login_response.json()["access_token"]

    profile_response = get_profile(base_url, access_token)

    assert profile_response.status_code == 200, profile_response.text
    profile = profile_response.json()
    assert profile["name"] == registered_user["payload"]["name"]
    assert profile["email"] == registered_user["payload"]["email"]

    new_password_response = login(
        base_url,
        {
            "email": registered_user["payload"]["email"],
            "password": duplicate_data["password"],
        },
    )

    assert new_password_response.status_code == 401, new_password_response.text
    assert new_password_response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_rejected_registration_does_not_reserve_email(base_url, user_data):
    invalid_data = user_data.copy()
    invalid_data["name"] = ""

    rejected_response = register(base_url, invalid_data)

    assert rejected_response.status_code == 422, rejected_response.text
    error_body = rejected_response.json()
    assert error_body["error"]["code"] == "VALIDATION_ERROR"

    assert any(
        detail["field"] == "body.name"
        for detail in error_body["error"]["details"]
    )

    login_response = login(
        base_url,
        {
            "email": user_data["email"],
            "password": user_data["password"],
        },
    )

    assert login_response.status_code == 401, login_response.text
    assert login_response.json()["error"]["code"] == "INVALID_CREDENTIALS"

    register_response = register(base_url, user_data)

    assert register_response.status_code == 201, register_response.text
    created_user = register_response.json()
    assert created_user["email"] == user_data["email"]
    assert created_user["name"] == user_data["name"]


def test_registered_password_is_case_sensitive(base_url, registered_user):
    login_data = {
        "email": registered_user["payload"]["email"],
        "password": registered_user["payload"]["password"],
    }

    login_response = login(base_url, login_data)

    assert login_response.status_code == 200, login_response.text

    password = registered_user["payload"]["password"]
    login_data["password"] = password[0].swapcase() + password[1:]

    invalid_login_response = login(base_url, login_data)

    assert invalid_login_response.status_code == 401, invalid_login_response.text
    assert invalid_login_response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_disabled_user_cannot_use_existing_token(
    base_url, registered_user, registered_login_data, admin_access_token
):
    login_response = login(base_url, registered_login_data)

    assert login_response.status_code == 200, login_response.text

    access_token = login_response.json()["access_token"]
    profile_response = get_profile(base_url, access_token)

    assert profile_response.status_code == 200, profile_response.text
    profile = profile_response.json()
    assert profile["email"] == registered_user["payload"]["email"]
    assert profile["is_active"] is True

    user_id = profile["id"]
    update_response = update_user_as_admin(
        base_url,
        admin_access_token,
        user_id,
        {"is_active": False},
    )

    assert update_response.status_code == 200, update_response.text
    updated_user = update_response.json()
    assert updated_user["id"] == user_id
    assert updated_user["is_active"] is False

    denied_response = get_profile(base_url, access_token)

    assert denied_response.status_code == 401, denied_response.text
    assert denied_response.json()["error"]["code"] == "UNAUTHORIZED"


def test_reactivated_user_can_use_existing_token_and_login(
    base_url, registered_user, registered_login_data, admin_access_token
):
    login_response = login(base_url, registered_login_data)

    assert login_response.status_code == 200, login_response.text

    access_token = login_response.json()["access_token"]
    profile_response = get_profile(base_url, access_token)

    assert profile_response.status_code == 200, profile_response.text

    original_profile = profile_response.json()

    assert original_profile["email"] == registered_user["payload"]["email"]
    assert original_profile["is_active"] is True

    user_id = original_profile["id"]
    disable_response = update_user_as_admin(
        base_url, admin_access_token, user_id, {"is_active": False}
    )

    assert disable_response.status_code == 200, disable_response.text
    disabled_user = disable_response.json()
    assert disabled_user["id"] == user_id
    assert disabled_user["is_active"] is False

    denied_response = get_profile(base_url, access_token)

    assert denied_response.status_code == 401, denied_response.text
    assert denied_response.json()["error"]["code"] == "UNAUTHORIZED"

    enable_response = update_user_as_admin(
        base_url, admin_access_token, user_id, {"is_active": True}
    )

    assert enable_response.status_code == 200, enable_response.text
    enabled_user = enable_response.json()
    assert enabled_user["id"] == user_id
    assert enabled_user["is_active"] is True

    restored_profile_response = get_profile(base_url, access_token)

    assert restored_profile_response.status_code == 200, restored_profile_response.text

    restored_profile = restored_profile_response.json()

    assert restored_profile["id"] == user_id
    assert restored_profile["email"] == original_profile["email"]
    assert restored_profile["name"] == original_profile["name"]
    assert restored_profile["is_active"] is True

    new_login_response = login(base_url, registered_login_data)

    assert new_login_response.status_code == 200, new_login_response.text

    new_access_token = new_login_response.json()["access_token"]

    assert isinstance(new_access_token, str)
    assert new_access_token


@pytest.mark.parametrize("password", VALID_ASCII_PASSWORD_CASES)
def test_register_and_login_with_allowed_ascii_password(base_url, user_data, password):
    user_data["password"] = password

    register_response = register(base_url, user_data)

    assert register_response.status_code == 201, register_response.text

    response = login(
        base_url,
        {"email": user_data["email"], "password": password},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body["access_token"], str)
    assert body["access_token"]


@pytest.mark.parametrize("domain", ASCII_EMAIL_DOMAINS)
def test_register_and_login_with_ascii_email(base_url, user_data, domain):
    local_part = user_data["email"].split("@")[0]
    expected_email = f"{local_part}+tag@{domain}"
    user_data["email"] = f"  {expected_email.upper()}  "

    register_response = register(base_url, user_data)

    assert register_response.status_code == 201, register_response.text
    assert register_response.json()["email"] == expected_email

    response = login(
        base_url,
        {"email": user_data["email"], "password": user_data["password"]},
    )

    assert response.status_code == 200, response.text
    assert response.json()["access_token"]


def test_register_and_login_with_max_email_length(base_url, user_data, email_254):
    user_data["email"] = f"  {email_254}  "

    register_response = register(base_url, user_data)

    assert register_response.status_code == 201, register_response.text
    assert register_response.json()["email"] == email_254

    response = login(
        base_url,
        {"email": f"  {email_254.upper()}  ", "password": user_data["password"]},
    )

    assert response.status_code == 200, response.text
    assert response.json()["access_token"]
