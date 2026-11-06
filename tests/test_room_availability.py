from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from api.bookings import create_booking, get_booking, list_bookings
from api.hotels import archive_hotel
from api.payments import get_payment
from api.rooms import archive_room, get_room_availability, update_room, update_room_availability
from data.booking import BOOKING_ROOM_DATA
from db import move_booking_expiry_to_past
from tests.assertions import assert_api_error


def assert_availability(response, room, stay, *, available, reason):
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["room_id"] == room["id"]
    for field, value in stay.items():
        assert body[field] == value
    assert body["available"] is available
    assert body["reason"] == reason
    nights = (date.fromisoformat(stay["check_out"]) - date.fromisoformat(stay["check_in"])).days
    assert type(body["nights"]) is int
    assert body["nights"] == nights
    assert isinstance(body["total_price"], str)
    assert Decimal(body["total_price"]) == Decimal(room["price_per_night"]) * nights
    assert body["currency"] == "RUB"
    assert response.headers.get("X-Request-ID")
    return body


@pytest.mark.parametrize("offset,nights,guests", [
    pytest.param(0, 1, 1, id="today-one-night-one-guest"),
    pytest.param(2, 1, 2, id="future-one-night-two-guests"),
    pytest.param(2, 14, 10, id="fourteen-nights-max-guests"),
])
def test_availability_accepts_stay_boundaries(base_url, admin_access_token, available_room, offset, nights, guests):
    room = available_room["room"]
    updated = update_room(base_url, admin_access_token, room["id"], {**BOOKING_ROOM_DATA, "capacity": 10})
    assert updated.status_code == 200, updated.text
    room = updated.json()
    assert room["capacity"] == 10
    check_in = datetime.now(timezone.utc).date() + timedelta(days=offset)
    stay = {"check_in": check_in.isoformat(), "check_out": (check_in + timedelta(days=nights)).isoformat(), "guests": guests}
    response = get_room_availability(base_url, room["id"], stay)
    assert_availability(response, room, stay, available=True, reason=None)


@pytest.mark.parametrize("field", ["check_in", "check_out", "guests", "all"])
def test_availability_requires_query_fields(base_url, available_room, stay_dates, field):
    params = stay_dates.copy()
    if field == "all":
        params = {}
    else:
        del params[field]
    response = get_room_availability(base_url, available_room["room"]["id"], params)
    body = assert_api_error(response, status=422, code="VALIDATION_ERROR")
    expected = ("check_in", "check_out", "guests") if field == "all" else (field,)
    for name in expected:
        assert any(item["field"] == f"query.{name}" for item in body["error"]["details"])


@pytest.mark.parametrize("guests", ["0", "11", "-1", "1.5", "true", "false", "text", "", "null"])
def test_availability_rejects_invalid_guests(base_url, available_room, stay_dates, guests):
    response = get_room_availability(base_url, available_room["room"]["id"], {**stay_dates, "guests": guests})
    body = assert_api_error(response, status=422, code="VALIDATION_ERROR")
    assert any(item["field"] == "query.guests" for item in body["error"]["details"])


@pytest.mark.parametrize("field", ["check_in", "check_out"])
@pytest.mark.parametrize("value", ["2030-02-30", "", "text", "2030-01-01T00:00:00Z", "2030-1-1", "1234567890", "null"])
def test_availability_rejects_invalid_date_format(base_url, available_room, stay_dates, field, value):
    response = get_room_availability(base_url, available_room["room"]["id"], {**stay_dates, field: value})
    body = assert_api_error(response, status=422, code="VALIDATION_ERROR")
    assert any(item["field"] == f"query.{field}" for item in body["error"]["details"])


@pytest.mark.parametrize("nights", [0, -1, 15])
def test_availability_rejects_invalid_duration(base_url, available_room, stay_dates, nights):
    check_in = date.fromisoformat(stay_dates["check_in"])
    response = get_room_availability(base_url, available_room["room"]["id"], {
        **stay_dates, "check_out": (check_in + timedelta(days=nights)).isoformat(),
    })
    assert_api_error(response, status=422, code="VALIDATION_ERROR")


def test_availability_rejects_past_check_in(base_url, available_room):
    today = datetime.now(timezone.utc).date()
    response = get_room_availability(base_url, available_room["room"]["id"], {
        "check_in": (today - timedelta(days=1)).isoformat(),
        "check_out": (today + timedelta(days=1)).isoformat(), "guests": 2,
    })
    assert_api_error(response, status=422, code="PAST_CHECK_IN")


@pytest.mark.parametrize("resource", ["unknown", "invalid_uuid", "archived_room", "archived_hotel"])
def test_availability_hides_missing_or_archived_resources(base_url, admin_access_token, available_room, stay_dates, resource):
    room_id = available_room["room"]["id"]
    if resource == "unknown":
        room_id = str(uuid4())
    elif resource == "invalid_uuid":
        room_id = "not-a-uuid"
    else:
        archived = (archive_room(base_url, admin_access_token, room_id) if resource == "archived_room"
                    else archive_hotel(base_url, admin_access_token, available_room["hotel"]["id"]))
        assert archived.status_code == 204, archived.text
    response = get_room_availability(base_url, room_id, stay_dates)
    assert_api_error(response, status=422 if resource == "invalid_uuid" else 404,
                     code="VALIDATION_ERROR" if resource == "invalid_uuid" else "NOT_FOUND")


@pytest.mark.parametrize("case,reason", [
    ("disabled", "ROOM_DISABLED"), ("capacity", "CAPACITY_EXCEEDED"), ("overlap", "ROOM_NOT_AVAILABLE"),
    ("disabled_capacity", "ROOM_DISABLED"), ("disabled_overlap", "ROOM_DISABLED"),
    ("capacity_overlap", "CAPACITY_EXCEEDED"), ("disabled_capacity_overlap", "ROOM_DISABLED"),
])
def test_availability_reason_priority(base_url, admin_access_token, available_room, pending_payment, stay_dates, user_access_token, case, reason):
    room = available_room["room"]
    booking = pending_payment["booking"]
    stay = stay_dates.copy()
    if "overlap" not in case:
        check_in = date.fromisoformat(booking["check_out"]) + timedelta(days=1)
        stay.update(check_in=check_in.isoformat(), check_out=(check_in + timedelta(days=1)).isoformat())
    if "capacity" in case:
        stay["guests"] = room["capacity"] + 1
        assert stay["guests"] <= 10
    if "disabled" in case:
        disabled = update_room_availability(base_url, admin_access_token, room["id"], {"is_available": False})
        assert disabled.status_code == 200, disabled.text
        assert disabled.json()["is_available"] is False
    response = get_room_availability(base_url, room["id"], stay)
    assert_availability(response, room, stay, available=False, reason=reason)
    saved = get_booking(base_url, user_access_token, booking["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == booking


def test_availability_get_does_not_reserve_room(base_url, available_room, stay_dates, user_access_token):
    room = available_room["room"]
    for _ in range(2):
        response = get_room_availability(base_url, room["id"], stay_dates)
        assert_availability(response, room, stay_dates, available=True, reason=None)
    before = list_bookings(base_url, user_access_token)
    assert before.status_code == 200, before.text
    assert before.json()["total"] == 0
    created = create_booking(base_url, user_access_token, {"room_id": room["id"], **stay_dates}, uuid4().hex)
    assert created.status_code == 201, created.text
    after = list_bookings(base_url, user_access_token)
    assert after.status_code == 200, after.text
    assert after.json()["total"] == 1
    assert [item["id"] for item in after.json()["items"]] == [created.json()["id"]]
    occupied = get_room_availability(base_url, room["id"], stay_dates)
    assert_availability(occupied, room, stay_dates, available=False, reason="ROOM_NOT_AVAILABLE")


@pytest.mark.db
def test_availability_releases_expired_hold(base_url, database_url, available_room, pending_payment, stay_dates, user_access_token):
    room = available_room["room"]
    booking = pending_payment["booking"]
    payment = pending_payment["payment"]
    occupied = get_room_availability(base_url, room["id"], stay_dates)
    assert_availability(occupied, room, stay_dates, available=False, reason="ROOM_NOT_AVAILABLE")
    expires_at = move_booking_expiry_to_past(database_url, booking["id"], booking["user_id"])
    response = get_room_availability(base_url, room["id"], stay_dates)
    assert_availability(response, room, stay_dates, available=True, reason=None)
    expired = get_booking(base_url, user_access_token, booking["id"])
    assert expired.status_code == 200, expired.text
    expired_body = expired.json()
    assert expired_body["status"] == "expired"
    assert datetime.fromisoformat(expired_body["expires_at"]) == expires_at
    for field in ("id", "user_id", "room_id", "check_in", "check_out", "guests", "price_per_night", "total_price", "currency"):
        assert expired_body[field] == booking[field]
    cancelled_payment = get_payment(base_url, user_access_token, payment["id"])
    assert cancelled_payment.status_code == 200, cancelled_payment.text
    assert cancelled_payment.json()["status"] == "cancelled"
    for field in ("id", "booking_id", "amount", "currency", "failure_reason"):
        assert cancelled_payment.json()[field] == payment[field]
