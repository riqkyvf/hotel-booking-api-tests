from datetime import datetime
from uuid import uuid4

import pytest

from api.auth import login
from api.bookings import get_booking
from api.payments import get_payment
from api.users import get_profile, get_user_as_admin, list_users_as_admin, update_user_as_admin
from tests.assertions import assert_api_error


@pytest.fixture
def managed_user(base_url, registered_user, admin_access_token):
    """Only this test-created user can be promoted; restore its ordinary role at teardown."""
    yield registered_user
    restored = update_user_as_admin(base_url, admin_access_token, registered_user["user"]["id"],
                                    {"role": "user", "is_active": True})
    assert restored.status_code == 200, restored.text
    assert restored.json()["role"] == "user"
    assert restored.json()["is_active"] is True


def test_admin_reads_user_without_secrets(base_url, admin_access_token, managed_user):
    response = get_user_as_admin(base_url, admin_access_token, managed_user["user"]["id"])
    assert response.status_code == 200, response.text
    assert response.json() == managed_user["user"]
    assert "password" not in response.json()
    assert "password_hash" not in response.json()
    assert managed_user["payload"]["password"] not in response.text
    assert response.headers.get("X-Request-ID")


@pytest.mark.parametrize("role,active", [("user", True), ("user", False), ("admin", True), ("admin", False)])
def test_admin_list_filters_include_matching_user(base_url, admin_access_token, managed_user, role, active):
    changed = update_user_as_admin(base_url, admin_access_token, managed_user["user"]["id"],
                                   {"role": role, "is_active": active})
    assert changed.status_code == 200, changed.text
    response = list_users_as_admin(base_url, admin_access_token,
                                   {"role": role, "is_active": active, "sort": "-created_at", "limit": 100})
    assert response.status_code == 200, response.text
    page = response.json()
    assert page["total"] >= 1
    assert changed.json()["id"] in {user["id"] for user in page["items"]}
    assert all(user["role"] == role and user["is_active"] is active for user in page["items"])
    for user in page["items"]:
        assert "password" not in user
        assert "password_hash" not in user


@pytest.mark.parametrize("sort", [None, "created_at", "-created_at", "email", "-email"])
def test_admin_list_sorting(base_url, admin_access_token, registered_user, sort):
    params = {"limit": 100}
    if sort is not None:
        params["sort"] = sort
    response = list_users_as_admin(base_url, admin_access_token, params)
    assert response.status_code == 200, response.text
    page = response.json()
    assert page["total"] >= len(page["items"]) > 0
    field = "email" if sort and "email" in sort else "created_at"
    values = [user[field] if field == "email" else datetime.fromisoformat(user[field]) for user in page["items"]]
    assert values == sorted(values, reverse=bool(sort and sort.startswith("-")))
    for left, right in zip(page["items"], page["items"][1:]):
        if left[field] == right[field]:
            assert left["id"] < right["id"]


def test_admin_list_pagination(base_url, admin_access_token, registered_user):
    baseline = list_users_as_admin(base_url, admin_access_token, {"limit": 4, "sort": "email"})
    assert baseline.status_code == 200, baseline.text
    expected = baseline.json()
    ids = []
    for offset in (0, 2):
        response = list_users_as_admin(base_url, admin_access_token, {"limit": 2, "offset": offset, "sort": "email"})
        assert response.status_code == 200, response.text
        page = response.json()
        assert page["limit"] == 2
        assert page["offset"] == offset
        assert page["total"] == expected["total"]
        assert page["items"] == expected["items"][offset:offset + 2]
        ids.extend(user["id"] for user in page["items"])
    assert len(ids) == len(set(ids))
    empty = list_users_as_admin(base_url, admin_access_token, {"offset": expected["total"]})
    assert empty.status_code == 200, empty.text
    assert empty.json()["items"] == []
    default = list_users_as_admin(base_url, admin_access_token)
    assert default.status_code == 200, default.text
    assert default.json()["limit"] == 20
    assert default.json()["offset"] == 0


@pytest.mark.parametrize("params", [
    {"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "bad"},
    {"role": "owner"}, {"is_active": "bad"},
])
def test_admin_list_rejects_invalid_query(base_url, admin_access_token, params):
    response = list_users_as_admin(base_url, admin_access_token, params)
    body = assert_api_error(response, status=422, code="VALIDATION_ERROR")
    assert any(item["field"] == f"query.{next(iter(params))}" for item in body["error"]["details"])


def test_admin_list_rejects_unknown_sort(base_url, admin_access_token):
    response = list_users_as_admin(base_url, admin_access_token, {"sort": "role"})
    assert_api_error(response, status=422, code="INVALID_SORT")


def test_role_changes_apply_to_existing_token(base_url, admin_access_token, managed_user, user_access_token):
    user_id = managed_user["user"]["id"]
    before = list_users_as_admin(base_url, user_access_token)
    assert_api_error(before, status=403, code="FORBIDDEN")
    promoted = update_user_as_admin(base_url, admin_access_token, user_id, {"role": "admin"})
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["role"] == "admin"
    allowed = list_users_as_admin(base_url, user_access_token)
    assert allowed.status_code == 200, allowed.text
    demoted = update_user_as_admin(base_url, admin_access_token, user_id, {"role": "user"})
    assert demoted.status_code == 200, demoted.text
    denied = list_users_as_admin(base_url, user_access_token)
    assert_api_error(denied, status=403, code="FORBIDDEN")
    profile = get_profile(base_url, user_access_token)
    assert profile.status_code == 200, profile.text
    assert profile.json() == demoted.json()


def test_deactivation_preserves_booking_and_payment(
    base_url, admin_access_token, managed_user, user_access_token, pending_payment,
):
    user_id = managed_user["user"]["id"]
    disabled = update_user_as_admin(base_url, admin_access_token, user_id, {"is_active": False})
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["is_active"] is False
    denied = get_profile(base_url, user_access_token)
    assert_api_error(denied, status=401, code="UNAUTHORIZED")
    for response, expected in (
        (get_booking(base_url, admin_access_token, pending_payment["booking"]["id"]), pending_payment["booking"]),
        (get_payment(base_url, admin_access_token, pending_payment["payment"]["id"]), pending_payment["payment"]),
    ):
        assert response.status_code == 200, response.text
        assert response.json() == expected
    enabled = update_user_as_admin(base_url, admin_access_token, user_id, {"is_active": True})
    assert enabled.status_code == 200, enabled.text
    profile = get_profile(base_url, user_access_token)
    assert profile.status_code == 200, profile.text
    assert profile.json() == enabled.json()
    logged_in = login(base_url, {field: managed_user["payload"][field] for field in ("email", "password")})
    assert logged_in.status_code == 200, logged_in.text


def test_admin_can_change_role_and_activity_together(base_url, admin_access_token, managed_user):
    response = update_user_as_admin(base_url, admin_access_token, managed_user["user"]["id"],
                                    {"role": "admin", "is_active": False})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["role"] == "admin"
    assert body["is_active"] is False
    for field in ("id", "email", "name", "phone", "created_at"):
        assert body[field] == managed_user["user"][field]
    saved = get_user_as_admin(base_url, admin_access_token, body["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == body


@pytest.mark.parametrize("payload", [
    {}, {"role": None}, {"is_active": None}, {"role": "owner"}, {"role": 1},
    {"is_active": "false"}, {"is_active": 0}, {"is_active": []},
    {"email": "must-not-save@example.com"}, {"password": "MustNotSave123!"},
    {"role": "admin", "unexpected": True}, {"role": "admin", "is_active": None},
])
def test_admin_patch_rejects_invalid_fields_without_partial_update(base_url, admin_access_token, managed_user, payload):
    user = managed_user["user"]
    response = update_user_as_admin(base_url, admin_access_token, user["id"], payload)
    assert_api_error(response, status=422, code="VALIDATION_ERROR")
    saved = get_user_as_admin(base_url, admin_access_token, user["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == user


@pytest.mark.parametrize("raw_body", ['{"role":', "[]"], ids=["malformed_json", "array"])
def test_admin_patch_rejects_invalid_json(base_url, admin_access_token, managed_user, raw_body):
    user = managed_user["user"]
    response = update_user_as_admin(base_url, admin_access_token, user["id"], raw_body=raw_body)
    assert_api_error(response, status=422, code="VALIDATION_ERROR")
    saved = get_user_as_admin(base_url, admin_access_token, user["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == user


@pytest.mark.parametrize("operation", ["read", "patch"])
@pytest.mark.parametrize("identifier,status,code", [(None, 404, "NOT_FOUND"), ("not-a-uuid", 422, "VALIDATION_ERROR")])
def test_admin_user_rejects_unknown_or_invalid_id(base_url, admin_access_token, operation, identifier, status, code):
    user_id = identifier or str(uuid4())
    response = (get_user_as_admin(base_url, admin_access_token, user_id) if operation == "read"
                else update_user_as_admin(base_url, admin_access_token, user_id, {"is_active": False}))
    assert_api_error(response, status=status, code=code)


@pytest.mark.parametrize("operation", ["list", "read", "patch"])
@pytest.mark.parametrize("token", [None, "invalid-token"], ids=["missing", "malformed"])
def test_admin_user_operations_require_valid_token(base_url, registered_user, admin_access_token, operation, token):
    user = registered_user["user"]
    if operation == "list":
        response = list_users_as_admin(base_url, token)
    elif operation == "read":
        response = get_user_as_admin(base_url, token, user["id"])
    else:
        response = update_user_as_admin(base_url, token, user["id"], {"role": "admin"})
    assert_api_error(response, status=401, code="UNAUTHORIZED")
    assert response.headers.get("WWW-Authenticate") == "Bearer"
    saved = get_user_as_admin(base_url, admin_access_token, user["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == user
