import pytest
import requests
from jsonschema import validate

from helpers.auth import login
from schemas.error_response import ERROR_SCHEMA


def test_login_with_valid_credentials(base_url, registered_login_data):
    response = login(base_url, registered_login_data)

    assert response.status_code == 200, response.text

    token_data = response.json()

    assert isinstance(token_data["access_token"], str)
    assert token_data["access_token"]
    assert token_data["token_type"] == "bearer"
    assert token_data["expires_in"] == 3600


@pytest.mark.parametrize("email_variant", ["uppercase", "spaces", "both"])
def test_login_normalizes_email(base_url, registered_login_data, email_variant):
    if email_variant in ["uppercase", "both"]:
        registered_login_data["email"] = registered_login_data["email"].upper()
    if email_variant in ["spaces", "both"]:
        registered_login_data["email"] = f"  {registered_login_data['email']}  "

    response = login(base_url, registered_login_data)

    assert response.status_code == 200, response.text

    access_token = response.json()["access_token"]

    assert isinstance(access_token, str)
    assert access_token


def test_login_with_invalid_password(base_url, registered_login_data):
    registered_login_data["password"] += "wrong"

    response = login(base_url, registered_login_data)

    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_with_disabled_user(base_url, disabled_user):
    response = login(
        base_url,
        {
            "email": disabled_user["email"],
            "password": disabled_user["password"],
        },
    )

    assert response.status_code == 401, response.text

    body = response.json()

    assert body["error"]["code"] == "INVALID_CREDENTIALS"
    assert "access_token" not in body


def test_login_with_nonexistent_email(base_url, login_data):
    response = login(base_url, login_data)

    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.parametrize("missing_field", ["email", "password"])
def test_login_without_required_field(base_url, login_data, missing_field):
    login_data.pop(missing_field)

    response = login(base_url, login_data)

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    assert any(
        detail["field"] == f"body.{missing_field}"
        for detail in response.json()["error"]["details"]
    )


@pytest.mark.parametrize("field", ["email", "password"])
def test_login_with_null_required_field(base_url, login_data, field):
    login_data[field] = None

    response = login(base_url, login_data)

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    assert any(
        detail["field"] == f"body.{field}"
        for detail in response.json()["error"]["details"]
    )


@pytest.mark.parametrize("field", ["email", "password"])
@pytest.mark.parametrize(
    "invalid_value",
    [1234567890, 1234567890.5, True, False, [], {}],
    ids=["integer", "float", "true", "false", "array", "object"],
)
def test_login_with_invalid_field_type(base_url, login_data, field, invalid_value):
    login_data[field] = invalid_value

    response = login(base_url, login_data)

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    assert any(
        detail["field"] == f"body.{field}"
        for detail in response.json()["error"]["details"]
    )


@pytest.mark.parametrize(
    "field, value",
    [
        ("name", "Evgeniy"),
        ("phone", "+79991234567"),
        ("role", "admin"),
        ("is_active", True),
        ("password_hash", "some-value"),
        ("unexpected", "value"),
    ],
    ids=["name", "phone", "role", "is_active", "password_hash", "unexpected"],
)
def test_login_with_extra_field(base_url, login_data, field, value):
    login_data[field] = value

    response = login(base_url, login_data)

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    assert any(
        detail["field"] == f"body.{field}"
        for detail in response.json()["error"]["details"]
    )


@pytest.mark.parametrize(
    "body",
    ["", "{}", '{"email":', "null", "[]", '"text"', "123", "true"],
    ids=[
        "no_body",
        "empty_object",
        "malformed_json",
        "null",
        "array",
        "string",
        "number",
        "boolean",
    ],
)
def test_login_with_invalid_body(base_url, body):
    response = requests.post(
        f"{base_url}/auth/login",
        data=body,
        headers={"Content-Type": "application/json"},
        timeout=10,
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    "email",
    ["", "   ", "userexample.com", "user@", "@example.com"],
    ids=["empty", "spaces", "without_at", "without_domain", "without_local_part"],
)
def test_login_with_invalid_email(base_url, login_data, email):
    login_data["email"] = email

    response = login(base_url, login_data)

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_login_with_empty_password(base_url, login_data):
    login_data["password"] = ""

    response = login(base_url, login_data)

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_login_invalid_credentials_error_response(base_url, registered_user, registered_login_data):
    successful_response = login(base_url, registered_login_data)

    assert successful_response.status_code == 200, successful_response.text

    access_token = successful_response.json()["access_token"]
    registered_login_data["password"] += "WrongPasswordMarker!"

    response = login(base_url, registered_login_data)

    assert response.status_code == 401, response.text

    body = response.json()
    validate(instance=body, schema=ERROR_SCHEMA)

    assert body["error"]["code"] == "INVALID_CREDENTIALS"
    assert response.headers.get("X-Request-ID")
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert registered_login_data["password"] not in response.text
    assert registered_user["password"] not in response.text
    assert access_token not in response.text
    assert "access_token" not in response.text
    assert "password_hash" not in response.text


def test_login_validation_error_response(base_url, login_data):
    login_data["password"] = "Q7!x"

    response = login(base_url, login_data)

    assert response.status_code == 422, response.text

    body = response.json()
    validate(instance=body, schema=ERROR_SCHEMA)

    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert any(detail["field"] == "body.password" for detail in body["error"]["details"])
    assert response.headers.get("X-Request-ID")
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]
    assert login_data["password"] not in response.text
    assert "access_token" not in response.text
    assert "password_hash" not in response.text
