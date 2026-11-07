from uuid import uuid4

import pytest
from jsonschema import validate

from api.auth import login, register
from api.users import get_profile, update_profile, update_user_as_admin
from data.auth import ASCII_EMAIL_DOMAINS, INVALID_EMAIL_CHARACTER_CASES
from data.profile import (
    FORBIDDEN_PROFILE_FIELDS,
    INVALID_PROFILE_ACCESS_TOKENS,
    INVALID_PROFILE_BODIES,
    INVALID_PROFILE_CHANGES,
    INVALID_PROFILE_FIELD_TYPES,
    VALID_PROFILE_FIELD_CHANGES,
)
from schemas.error_response import ERROR_SCHEMA
from tests.assertions import assert_api_error


@pytest.fixture
def profile_before(base_url, user_access_token):
    response = get_profile(base_url, user_access_token)

    assert response.status_code == 200, response.text

    return response.json()


@pytest.fixture
def other_registered_user(base_url, user_data):
    payload = user_data.copy()
    payload["email"] = f"other_{uuid4().hex}@example.com"
    response = register(base_url, payload)

    assert response.status_code == 201, response.text

    return {"payload": payload, "user": response.json()}


@pytest.mark.parametrize("domain", ASCII_EMAIL_DOMAINS)
def test_update_profile_all_fields(
    base_url, registered_user, user_access_token, profile_before, domain
):
    local_part = profile_before["email"].split("@")[0]
    expected_email = f"updated_{local_part}+tag@{domain}"
    response = update_profile(
        base_url,
        user_access_token,
        {
            "email": f"  {expected_email.upper()}  ",
            "name": "  Changed Name  ",
            "phone": "+79991234567",
        },
    )

    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["email"] == expected_email
    assert updated["name"] == "Changed Name"
    assert updated["phone"] == "+79991234567"
    for field in ("id", "role", "is_active", "created_at"):
        assert updated[field] == profile_before[field]
    assert "password" not in updated
    assert "password_hash" not in updated
    assert response.headers.get("X-Request-ID")

    saved = get_profile(base_url, user_access_token)
    assert saved.status_code == 200, saved.text
    assert saved.json() == updated

    password = registered_user["payload"]["password"]
    new_login = login(base_url, {"email": expected_email, "password": password})
    assert new_login.status_code == 200, new_login.text
    assert new_login.json()["access_token"]

    old_login = login(base_url, {"email": profile_before["email"], "password": password})
    assert old_login.status_code == 401, old_login.text
    assert old_login.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.parametrize("field,value,expected", VALID_PROFILE_FIELD_CHANGES)
def test_update_profile_single_field(
    base_url, user_access_token, profile_before, field, value, expected
):
    response = update_profile(base_url, user_access_token, {field: value})

    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated[field] == expected
    for unchanged in ("id", "email", "name", "phone", "role", "is_active", "created_at"):
        if unchanged != field:
            assert updated[unchanged] == profile_before[unchanged]
    assert "password" not in updated
    assert "password_hash" not in updated

    saved = get_profile(base_url, user_access_token)
    assert saved.status_code == 200, saved.text
    assert saved.json() == updated


def test_update_profile_preserves_omitted_fields(base_url, user_access_token, profile_before):
    email = "updated_" + profile_before["email"]
    setup = update_profile(
        base_url,
        user_access_token,
        {"email": email, "phone": "+79991234567"},
    )
    assert setup.status_code == 200, setup.text

    response = update_profile(base_url, user_access_token, {"name": "Only Name Changed"})

    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["name"] == "Only Name Changed"
    setup_body = setup.json()
    for field in ("id", "email", "phone", "role", "is_active", "created_at"):
        assert updated[field] == setup_body[field]

    saved = get_profile(base_url, user_access_token)
    assert saved.status_code == 200, saved.text
    assert saved.json() == updated


def test_update_profile_can_clear_phone(base_url, user_access_token, profile_before):
    setup = update_profile(base_url, user_access_token, {"phone": "+79991234567"})
    assert setup.status_code == 200, setup.text
    assert setup.json()["phone"] == "+79991234567"

    response = update_profile(base_url, user_access_token, {"phone": None})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["phone"] is None
    for field in ("id", "email", "name", "role", "is_active", "created_at"):
        assert body[field] == profile_before[field]

    saved = get_profile(base_url, user_access_token)
    assert saved.status_code == 200, saved.text
    assert saved.json() == body


@pytest.mark.parametrize("padding", ["", "  "], ids=["exact", "with_outer_spaces"])
def test_update_profile_with_max_email_length(
    base_url, user_access_token, profile_before, email_254, padding
):
    response = update_profile(
        base_url, user_access_token, {"email": f"{padding}{email_254}{padding}"}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email"] == email_254
    assert body["id"] == profile_before["id"]

    saved = get_profile(base_url, user_access_token)
    assert saved.status_code == 200, saved.text
    assert saved.json() == body


@pytest.mark.parametrize("variant", ["original", "uppercase", "spaces", "both"])
def test_update_profile_with_own_email(base_url, user_access_token, profile_before, variant):
    email = profile_before["email"]
    if variant in ("uppercase", "both"):
        email = email.upper()
    if variant in ("spaces", "both"):
        email = f"  {email}  "

    response = update_profile(base_url, user_access_token, {"email": email})

    assert response.status_code == 200, response.text
    body = response.json()
    for field in ("id", "email", "name", "phone", "role", "is_active", "created_at"):
        assert body[field] == profile_before[field]

    saved = get_profile(base_url, user_access_token)
    assert saved.status_code == 200, saved.text
    assert saved.json() == body


@pytest.mark.parametrize("variant", ["original", "uppercase", "spaces", "both"])
def test_update_profile_rejects_existing_email(
    base_url, user_access_token, profile_before, other_registered_user, variant
):
    email = other_registered_user["user"]["email"]
    if variant in ("uppercase", "both"):
        email = email.upper()
    if variant in ("spaces", "both"):
        email = f"  {email}  "

    response = update_profile(
        base_url,
        user_access_token,
        {"email": email, "name": "Must Not Be Saved", "phone": "+79991234567"},
    )

    assert_api_error(response, status=409, code="EMAIL_EXISTS")

    saved = get_profile(base_url, user_access_token)
    assert saved.status_code == 200, saved.text
    assert saved.json() == profile_before


@pytest.mark.parametrize("email", INVALID_EMAIL_CHARACTER_CASES)
def test_update_profile_rejects_invalid_email_characters(
    base_url, user_access_token, profile_before, email
):
    response = update_profile(
        base_url, user_access_token, {"email": email, "name": "Must Not Be Saved"}
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert any(detail["field"] == "body.email" for detail in body["error"]["details"])

    saved = get_profile(base_url, user_access_token)
    assert saved.status_code == 200, saved.text
    assert saved.json() == profile_before


@pytest.mark.parametrize("changes,error_field", INVALID_PROFILE_CHANGES)
def test_update_profile_rejects_invalid_values(
    base_url, user_access_token, profile_before, changes, error_field
):
    response = update_profile(base_url, user_access_token, changes)

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    if error_field is not None:
        assert any(detail["field"] == error_field for detail in body["error"]["details"])

    saved = get_profile(base_url, user_access_token)
    assert saved.status_code == 200, saved.text
    assert saved.json() == profile_before


@pytest.mark.parametrize("field", ["email", "name", "phone"])
@pytest.mark.parametrize("value", INVALID_PROFILE_FIELD_TYPES)
def test_update_profile_rejects_invalid_types(
    base_url, user_access_token, profile_before, field, value
):
    response = update_profile(base_url, user_access_token, {field: value})

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert any(detail["field"] == f"body.{field}" for detail in body["error"]["details"])

    saved = get_profile(base_url, user_access_token)
    assert saved.status_code == 200, saved.text
    assert saved.json() == profile_before


@pytest.mark.parametrize("field,value", FORBIDDEN_PROFILE_FIELDS)
def test_update_profile_rejects_forbidden_fields(
    base_url, user_access_token, profile_before, field, value
):
    response = update_profile(
        base_url, user_access_token, {"name": "Must Not Be Saved", field: value}
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert any(detail["field"] == f"body.{field}" for detail in body["error"]["details"])

    saved = get_profile(base_url, user_access_token)
    assert saved.status_code == 200, saved.text
    assert saved.json() == profile_before


@pytest.mark.parametrize("body", INVALID_PROFILE_BODIES)
def test_update_profile_rejects_invalid_body(
    base_url, user_access_token, profile_before, body
):
    response = update_profile(base_url, user_access_token, raw_body=body)

    assert response.status_code == 422, response.text
    response_body = response.json()
    validate(instance=response_body, schema=ERROR_SCHEMA)
    assert response_body["error"]["code"] == "VALIDATION_ERROR"

    saved = get_profile(base_url, user_access_token)
    assert saved.status_code == 200, saved.text
    assert saved.json() == profile_before


@pytest.mark.parametrize("padding", ["", "  "], ids=["exact", "with_outer_spaces"])
def test_update_profile_rejects_email_exceeding_max_length(
    base_url, user_access_token, profile_before, email_254, padding
):
    response = update_profile(
        base_url, user_access_token, {"email": f"{padding}{email_254}c{padding}"}
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert any(detail["field"] == "body.email" for detail in body["error"]["details"])

    saved = get_profile(base_url, user_access_token)
    assert saved.status_code == 200, saved.text
    assert saved.json() == profile_before


@pytest.mark.parametrize("access_token", INVALID_PROFILE_ACCESS_TOKENS)
def test_update_profile_requires_authorization(
    base_url, user_access_token, profile_before, access_token
):
    response = update_profile(base_url, access_token, {"name": "Must Not Be Saved"})

    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert response.headers["WWW-Authenticate"] == "Bearer"

    saved = get_profile(base_url, user_access_token)
    assert saved.status_code == 200, saved.text
    assert saved.json() == profile_before


def test_disabled_user_cannot_update_profile(
    base_url, registered_user, user_access_token, admin_access_token
):
    disabled = update_user_as_admin(
        base_url,
        admin_access_token,
        registered_user["user"]["id"],
        {"is_active": False},
    )
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["is_active"] is False

    response = update_profile(base_url, user_access_token, {"name": "Must Not Be Saved"})

    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_update_profile_changes_only_current_user(
    base_url, user_access_token, profile_before, other_registered_user
):
    response = update_profile(base_url, user_access_token, {"name": "Only Current User"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == profile_before["id"]
    assert body["name"] == "Only Current User"

    other_login = login(
        base_url,
        {
            "email": other_registered_user["payload"]["email"],
            "password": other_registered_user["payload"]["password"],
        },
    )
    assert other_login.status_code == 200, other_login.text

    other_profile = get_profile(base_url, other_login.json()["access_token"])
    assert other_profile.status_code == 200, other_profile.text
    assert other_profile.json() == other_registered_user["user"]


def test_update_profile_validation_error_response(
    base_url, user_access_token, profile_before
):
    password_marker = "ProfileSecretMarker!"
    response = update_profile(
        base_url,
        user_access_token,
        {"password": password_marker, "name": "Must Not Be Saved"},
    )

    body = assert_api_error(response, status=422, code="VALIDATION_ERROR")
    assert any(detail["field"] == "body.password" for detail in body["error"]["details"])
    assert password_marker not in response.text
    assert user_access_token not in response.text
    assert "access_token" not in response.text

    saved = get_profile(base_url, user_access_token)
    assert saved.status_code == 200, saved.text
    assert saved.json() == profile_before
