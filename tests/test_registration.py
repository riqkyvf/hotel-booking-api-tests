import pytest
from jsonschema import validate

from api.auth import register
from data.auth import INVALID_EMAIL_CHARACTER_CASES, INVALID_PASSWORD_CHARACTER_CASES
from schemas.error_response import ERROR_SCHEMA


def test_register_without_phone(base_url, user_data):
    response = register(base_url, user_data)

    assert response.status_code == 201, response.text

    user = response.json()

    assert user["email"] == user_data["email"]
    assert user["name"] == user_data["name"]
    assert user["phone"] is None
    assert user["role"] == "user"
    assert user["is_active"] is True

    assert "password" not in user
    assert "password_hash" not in user


def test_register_with_phone(base_url, user_data):
    user_data["phone"] = "79231952356"
    response = register(base_url, user_data)

    assert response.status_code == 201, response.text

    user = response.json()

    assert user["email"] == user_data["email"]
    assert user["name"] == user_data["name"]
    assert user["phone"] == user_data["phone"]
    assert user["role"] == "user"
    assert user["is_active"] is True

    assert "password" not in user
    assert "password_hash" not in user


@pytest.mark.parametrize("email_variant", ["original", "uppercase", "spaces"])
def test_register_with_existing_email(base_url, registered_user, email_variant):
    duplicate_data = registered_user["payload"].copy()

    if email_variant == "uppercase":
        duplicate_data["email"] = duplicate_data["email"].upper()
    elif email_variant == "spaces":
        duplicate_data["email"] = f"  {duplicate_data['email']}  "

    response = register(base_url, duplicate_data)

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "EMAIL_EXISTS"


@pytest.mark.parametrize("missing_field", ["email", "password", "name"])
def test_register_without_required_field(base_url, user_data, missing_field):
    user_data.pop(missing_field)

    response = register(base_url, user_data)

    assert response.status_code == 422, response.text

    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"

    assert any(
        detail["field"] == f"body.{missing_field}"
        for detail in body["error"]["details"]
    )


@pytest.mark.parametrize("password_length", [0, 9, 129])
def test_register_with_invalid_password_length(base_url, user_data, password_length):
    user_data["password"] = "a" * password_length

    response = register(base_url, user_data)

    assert response.status_code == 422, response.text

    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"

    assert any(
        detail["field"] == "body.password"
        for detail in body["error"]["details"]
    )


@pytest.mark.parametrize("password_length", [10, 128])
def test_register_with_valid_password_length(base_url, user_data, password_length):
    user_data["password"] = "a" * password_length

    response = register(base_url, user_data)

    assert response.status_code == 201, response.text


@pytest.mark.parametrize(
    "name",
    ["", "  ", "a" * 101],
    ids=["empty", "spaces", "too_long"],
)
def test_register_with_invalid_name(base_url, user_data, name):
    user_data["name"] = name

    response = register(base_url, user_data)

    assert response.status_code == 422, response.text

    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"

    assert any(
        detail["field"] == "body.name"
        for detail in body["error"]["details"]
    )


@pytest.mark.parametrize("name_length", [1, 100])
def test_register_with_valid_name_length(base_url, user_data, name_length):
    user_data["name"] = "a" * name_length

    response = register(base_url, user_data)

    assert response.status_code == 201, response.text
    assert response.json()["name"] == user_data["name"]


@pytest.mark.parametrize(
    "name, expected_name",
    [
        ("  Evgeniy  ", "Evgeniy"),
        ("  a  ", "a"),
        ("  " + "a" * 100 + "  ", "a" * 100),
    ],
    ids=["regular_name", "min_length", "max_length"],
)
def test_register_trims_name(base_url, user_data, name, expected_name):
    user_data["name"] = name

    response = register(base_url, user_data)

    assert response.status_code == 201, response.text
    assert response.json()["name"] == expected_name


@pytest.mark.parametrize(
    "leading_spaces, trailing_spaces",
    [("  ", ""), ("", "  "), ("  ", "  ")],
    ids=["leading", "trailing", "both"],
)
def test_register_trims_email(base_url, user_data, leading_spaces, trailing_spaces):
    expected_email = user_data["email"]
    user_data["email"] = f"{leading_spaces}{expected_email}{trailing_spaces}"

    response = register(base_url, user_data)

    assert response.status_code == 201, response.text
    assert response.json()["email"] == expected_email


def test_register_lowercases_email(base_url, user_data):
    expected_email = user_data["email"]
    user_data["email"] = expected_email.upper()

    response = register(base_url, user_data)

    assert response.status_code == 201, response.text
    assert response.json()["email"] == expected_email


@pytest.mark.parametrize(
    "email",
    ["userexample.com", "user@", "@example.com", "", "   "],
    ids=["without_at", "without_domain", "without_local_part", "empty", "spaces"],
)
def test_register_with_invalid_email(base_url, user_data, email):
    user_data["email"] = email

    response = register(base_url, user_data)

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"

    assert any(
        detail["field"] == "body.email"
        for detail in body["error"]["details"]
    )


@pytest.mark.parametrize("field", ["email", "password", "name"])
def test_register_with_null_required_field(base_url, user_data, field):
    user_data[field] = None

    response = register(base_url, user_data)

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"

    assert any(
        detail["field"] == f"body.{field}"
        for detail in body["error"]["details"]
    )


@pytest.mark.parametrize("field", ["email", "password", "name", "phone"])
@pytest.mark.parametrize(
    "invalid_value",
    [1234567890, 1234567890.5, True, False, [], {}],
    ids=["integer", "float", "true", "false", "array", "object"],
)
def test_register_with_invalid_field_type(base_url, user_data, field, invalid_value):
    user_data[field] = invalid_value

    response = register(base_url, user_data)

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"

    assert any(
        detail["field"] == f"body.{field}"
        for detail in body["error"]["details"]
    )


@pytest.mark.parametrize("padding", ["", "  "], ids=["exact", "with_outer_spaces"])
def test_register_with_max_email_length(base_url, user_data, email_254, padding):
    user_data["email"] = f"{padding}{email_254}{padding}"

    assert len(email_254) == 254

    response = register(base_url, user_data)

    assert response.status_code == 201, response.text
    assert response.json()["email"] == email_254


def test_register_with_email_exceeding_max_length(base_url, user_data, email_254):
    user_data["email"] = email_254 + "c"

    assert len(user_data["email"]) == 255

    response = register(base_url, user_data)

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"

    assert any(
        detail["field"] == "body.email"
        for detail in body["error"]["details"]
    )


@pytest.mark.parametrize("phone_length", [7, 15])
@pytest.mark.parametrize("prefix", ["", "+"], ids=["without_plus", "with_plus"])
def test_register_with_valid_phone_length(base_url, user_data, phone_length, prefix):
    user_data["phone"] = prefix + "7" * phone_length

    response = register(base_url, user_data)

    assert response.status_code == 201, response.text
    assert response.json()["phone"] == user_data["phone"]


@pytest.mark.parametrize("phone_length", [6, 16])
@pytest.mark.parametrize("prefix", ["", "+"], ids=["without_plus", "with_plus"])
def test_register_with_invalid_phone_length(base_url, user_data, phone_length, prefix):
    user_data["phone"] = prefix + "7" * phone_length

    response = register(base_url, user_data)

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"

    assert any(
        detail["field"] == "body.phone"
        for detail in body["error"]["details"]
    )


def test_register_with_null_phone(base_url, user_data):
    user_data["phone"] = None

    response = register(base_url, user_data)

    assert response.status_code == 201, response.text
    assert response.json()["phone"] is None


@pytest.mark.parametrize(
    "phone",
    [
        "",
        "   ",
        "+7999abc4567",
        "+7999абв4567",
        "7999-1234567",
        "(7999)1234567",
        "7999 1234567",
        "++79991234567",
        "79991234567+",
        "+",
    ],
    ids=[
        "empty",
        "spaces",
        "latin_letters",
        "cyrillic_letters",
        "hyphen",
        "parentheses",
        "internal_space",
        "double_plus",
        "trailing_plus",
        "only_plus",
    ],
)
def test_register_with_invalid_phone(base_url, user_data, phone):
    user_data["phone"] = phone

    response = register(base_url, user_data)

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"

    assert any(
        detail["field"] == "body.phone"
        for detail in body["error"]["details"]
    )


@pytest.mark.parametrize(
    "field, value",
    [
        ("role", "admin"),
        ("is_active", False),
        ("password_hash", "some-value"),
        ("unexpected", "value"),
        ("id", "e2e186d6-7682-466a-812e-b6367d9e4343"),
        ("created_at", "2026-11-01T00:00:00Z"),
        ("updated_at", "2026-11-01T00:00:00Z"),
    ],
    ids=["role", "is_active", "password_hash", "unexpected", "id", "created_at", "updated_at"],
)
def test_register_with_extra_field(base_url, user_data, field, value):
    user_data[field] = value

    response = register(base_url, user_data)

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"

    assert any(
        detail["field"] == f"body.{field}"
        for detail in body["error"]["details"]
    )


@pytest.mark.parametrize(
    "body",
    ["", "{}", '{"email":'],
    ids=["no_body", "empty_object", "malformed_json"],
)
def test_register_with_invalid_body(base_url, body):
    response = register(base_url, raw_body=body)

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_register_validation_error_response(base_url, user_data):
    user_data["password"] = "Q7!x"

    response = register(base_url, user_data)

    assert response.status_code == 422, response.text

    body = response.json()
    validate(instance=body, schema=ERROR_SCHEMA)

    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert any(detail["field"] == "body.password" for detail in body["error"]["details"])
    assert response.headers.get("X-Request-ID")
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]
    assert user_data["password"] not in response.text
    assert "password_hash" not in response.text


def test_register_duplicate_email_error_response(base_url, registered_user):
    response = register(base_url, registered_user["payload"])

    assert response.status_code == 409, response.text

    body = response.json()
    validate(instance=body, schema=ERROR_SCHEMA)

    assert body["error"]["code"] == "EMAIL_EXISTS"
    assert response.headers.get("X-Request-ID")
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]
    assert registered_user["payload"]["password"] not in response.text
    assert "password_hash" not in response.text


def test_register_with_cyrillic_name(base_url, user_data):
    user_data["name"] = "Евгений"

    response = register(base_url, user_data)

    assert response.status_code == 201, response.text
    assert response.json()["name"] == user_data["name"]


@pytest.mark.parametrize("invalid_email_characters", INVALID_EMAIL_CHARACTER_CASES)
def test_register_with_invalid_email_characters(
    base_url, user_data, invalid_email_characters
):
    user_data["email"] = invalid_email_characters

    response = register(base_url, user_data)

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert any(detail["field"] == "body.email" for detail in body["error"]["details"])


@pytest.mark.parametrize("invalid_password_characters", INVALID_PASSWORD_CHARACTER_CASES)
def test_register_with_invalid_password_characters(
    base_url, user_data, invalid_password_characters
):
    user_data["password"] = invalid_password_characters

    response = register(base_url, user_data)

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert any(detail["field"] == "body.password" for detail in body["error"]["details"])
