from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from jsonschema import validate

from api.bookings import create_booking, get_booking, list_bookings
from api.rooms import archive_room, get_room, get_room_availability, update_room_availability
from data.booking import INVALID_CHECK_OUT_OFFSETS, VALID_STAY_BOUNDARIES
from schemas.error_response import ERROR_SCHEMA


def test_booking_with_past_check_in_is_rejected(base_url, available_room, stay_dates, user_access_token):
    today = datetime.now(timezone.utc).date()
    payload = {
        "room_id": available_room["room"]["id"],
        "check_in": (today - timedelta(days=1)).isoformat(),
        "check_out": (today + timedelta(days=1)).isoformat(),
        "guests": stay_dates["guests"],
    }
    response = create_booking(base_url, user_access_token, payload, uuid4().hex)
    assert response.status_code == 422, response.text
    body = response.json()
    validate(instance=body, schema=ERROR_SCHEMA)
    assert body["error"]["code"] == "PAST_CHECK_IN"
    assert response.headers.get("X-Request-ID")
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]

    bookings = list_bookings(base_url, user_access_token)
    assert bookings.status_code == 200, bookings.text
    page = bookings.json()
    assert page["total"] == 0
    assert page["items"] == []


@pytest.mark.parametrize("check_out_offset", INVALID_CHECK_OUT_OFFSETS)
def test_booking_with_check_out_not_after_check_in_is_rejected(
    base_url, available_room, stay_dates, user_access_token, check_out_offset,
):
    check_in = date.fromisoformat(stay_dates["check_in"])
    payload = {
        "room_id": available_room["room"]["id"],
        **stay_dates,
        "check_out": (check_in + timedelta(days=check_out_offset)).isoformat(),
    }
    response = create_booking(base_url, user_access_token, payload, uuid4().hex)
    assert response.status_code == 422, response.text
    body = response.json()
    validate(instance=body, schema=ERROR_SCHEMA)
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert any(detail["field"] == "body" for detail in body["error"]["details"])
    assert response.headers.get("X-Request-ID")
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]

    bookings = list_bookings(base_url, user_access_token)
    assert bookings.status_code == 200, bookings.text
    page = bookings.json()
    assert page["total"] == 0
    assert page["items"] == []


def test_booking_exceeding_room_capacity_is_rejected(
    base_url, available_room, stay_dates, user_access_token,
):
    room = available_room["room"]
    guests = room["capacity"] + 1
    assert guests <= 10
    stay = {**stay_dates, "guests": guests}
    availability = get_room_availability(base_url, room["id"], stay)
    assert availability.status_code == 200, availability.text
    unavailable = availability.json()
    assert unavailable["room_id"] == room["id"]
    assert unavailable["available"] is False
    assert unavailable["reason"] == "CAPACITY_EXCEEDED"

    payload = {"room_id": room["id"], **stay}
    response = create_booking(base_url, user_access_token, payload, uuid4().hex)
    assert response.status_code == 409, response.text
    body = response.json()
    validate(instance=body, schema=ERROR_SCHEMA)
    assert body["error"]["code"] == "CAPACITY_EXCEEDED"
    assert response.headers.get("X-Request-ID")
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]

    bookings = list_bookings(base_url, user_access_token)
    assert bookings.status_code == 200, bookings.text
    page = bookings.json()
    assert page["total"] == 0
    assert page["items"] == []


def test_booking_disabled_room_is_rejected(
    base_url, available_room, stay_dates, user_access_token, admin_access_token,
):
    room_id = available_room["room"]["id"]
    disabled = update_room_availability(
        base_url, admin_access_token, room_id, {"is_available": False},
    )
    assert disabled.status_code == 200, disabled.text
    disabled_room = disabled.json()
    assert disabled_room["id"] == room_id
    assert disabled_room["is_available"] is False

    stay = stay_dates
    availability = get_room_availability(base_url, room_id, stay)
    assert availability.status_code == 200, availability.text
    unavailable = availability.json()
    assert unavailable["room_id"] == room_id
    assert unavailable["available"] is False
    assert unavailable["reason"] == "ROOM_DISABLED"

    response = create_booking(base_url, user_access_token, {"room_id": room_id, **stay}, uuid4().hex)
    assert response.status_code == 409, response.text
    body = response.json()
    validate(instance=body, schema=ERROR_SCHEMA)
    assert body["error"]["code"] == "ROOM_DISABLED"
    assert response.headers.get("X-Request-ID")
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]

    bookings = list_bookings(base_url, user_access_token)
    assert bookings.status_code == 200, bookings.text
    page = bookings.json()
    assert page["total"] == 0
    assert page["items"] == []
    saved_room = get_room(base_url, room_id)
    assert saved_room.status_code == 200, saved_room.text
    assert saved_room.json() == disabled_room


def test_booking_archived_room_is_rejected(
    base_url, available_room, stay_dates, user_access_token, admin_access_token,
):
    room_id = available_room["room"]["id"]
    archived = archive_room(base_url, admin_access_token, room_id)
    assert archived.status_code == 204, archived.text

    stay = stay_dates
    availability = get_room_availability(base_url, room_id, stay)
    assert availability.status_code == 404, availability.text
    unavailable = availability.json()
    validate(instance=unavailable, schema=ERROR_SCHEMA)
    assert unavailable["error"]["code"] == "NOT_FOUND"

    response = create_booking(base_url, user_access_token, {"room_id": room_id, **stay}, uuid4().hex)
    assert response.status_code == 404, response.text
    body = response.json()
    validate(instance=body, schema=ERROR_SCHEMA)
    assert body["error"]["code"] == "NOT_FOUND"
    assert response.headers.get("X-Request-ID")
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]

    bookings = list_bookings(base_url, user_access_token)
    assert bookings.status_code == 200, bookings.text
    page = bookings.json()
    assert page["total"] == 0
    assert page["items"] == []


@pytest.mark.parametrize("check_in_offset,nights", VALID_STAY_BOUNDARIES)
def test_booking_with_valid_stay_boundaries_is_allowed(
    base_url, available_room, stay_dates, registered_user, user_access_token, check_in_offset, nights,
):
    room = available_room["room"]
    check_in = datetime.now(timezone.utc).date() + timedelta(days=check_in_offset)
    stay = {
        "check_in": check_in.isoformat(),
        "check_out": (check_in + timedelta(days=nights)).isoformat(),
        "guests": stay_dates["guests"],
    }
    expected_total = Decimal(room["price_per_night"]) * nights
    availability = get_room_availability(base_url, room["id"], stay)
    assert availability.status_code == 200, availability.text
    available = availability.json()
    assert available["room_id"] == room["id"]
    assert available["available"] is True
    assert available["reason"] is None
    for field, value in stay.items():
        assert available[field] == value
    assert available["nights"] == nights
    assert isinstance(available["total_price"], str)
    assert Decimal(available["total_price"]) == expected_total
    assert available["currency"] == "RUB"

    payload = {"room_id": room["id"], **stay}
    response = create_booking(base_url, user_access_token, payload, uuid4().hex)
    assert response.status_code == 201, response.text
    booking = response.json()
    assert booking["status"] == "pending_payment"
    assert booking["user_id"] == registered_user["user"]["id"]
    for field, value in payload.items():
        assert booking[field] == value
    assert isinstance(booking["price_per_night"], str)
    assert isinstance(booking["total_price"], str)
    assert Decimal(booking["price_per_night"]) == Decimal(room["price_per_night"])
    assert Decimal(booking["total_price"]) == expected_total
    assert booking["currency"] == "RUB"
    assert response.headers.get("X-Request-ID")

    saved = get_booking(base_url, user_access_token, booking["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == booking
    bookings = list_bookings(base_url, user_access_token)
    assert bookings.status_code == 200, bookings.text
    page = bookings.json()
    assert page["total"] == 1
    assert [item["id"] for item in page["items"]] == [booking["id"]]


def test_booking_longer_than_fourteen_nights_is_rejected(
    base_url, available_room, stay_dates, user_access_token,
):
    check_in = date.fromisoformat(stay_dates["check_in"])
    stay = {
        **stay_dates,
        "check_out": (check_in + timedelta(days=15)).isoformat(),
    }
    room_id = available_room["room"]["id"]
    availability = get_room_availability(base_url, room_id, stay)
    assert availability.status_code == 422, availability.text
    invalid_stay = availability.json()
    validate(instance=invalid_stay, schema=ERROR_SCHEMA)
    assert invalid_stay["error"]["code"] == "VALIDATION_ERROR"

    response = create_booking(base_url, user_access_token, {"room_id": room_id, **stay}, uuid4().hex)
    assert response.status_code == 422, response.text
    body = response.json()
    validate(instance=body, schema=ERROR_SCHEMA)
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert any(detail["field"] == "body" for detail in body["error"]["details"])
    assert response.headers.get("X-Request-ID")
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]

    bookings = list_bookings(base_url, user_access_token)
    assert bookings.status_code == 200, bookings.text
    page = bookings.json()
    assert page["total"] == 0
    assert page["items"] == []
