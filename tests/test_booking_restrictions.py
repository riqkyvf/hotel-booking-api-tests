from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from jsonschema import validate

from api.bookings import create_booking, list_bookings
from api.rooms import archive_room, get_room, get_room_availability, update_room_availability
from data.booking import INVALID_CHECK_OUT_OFFSETS
from schemas.error_response import ERROR_SCHEMA


def test_booking_with_past_check_in_is_rejected(base_url, available_room, user_access_token):
    today = datetime.now(timezone.utc).date()
    payload = {
        "room_id": available_room["room"]["id"],
        "check_in": (today - timedelta(days=1)).isoformat(),
        "check_out": (today + timedelta(days=1)).isoformat(),
        "guests": available_room["stay"]["guests"],
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
    base_url, available_room, user_access_token, check_out_offset,
):
    check_in = date.fromisoformat(available_room["stay"]["check_in"])
    payload = {
        "room_id": available_room["room"]["id"],
        **available_room["stay"],
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
    base_url, available_room, user_access_token,
):
    room = available_room["room"]
    guests = room["capacity"] + 1
    assert guests <= 10
    stay = {**available_room["stay"], "guests": guests}
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
    base_url, available_room, user_access_token, admin_access_token,
):
    room_id = available_room["room"]["id"]
    disabled = update_room_availability(
        base_url, admin_access_token, room_id, {"is_available": False},
    )
    assert disabled.status_code == 200, disabled.text
    disabled_room = disabled.json()
    assert disabled_room["id"] == room_id
    assert disabled_room["is_available"] is False

    stay = available_room["stay"]
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
    base_url, available_room, user_access_token, admin_access_token,
):
    room_id = available_room["room"]["id"]
    archived = archive_room(base_url, admin_access_token, room_id)
    assert archived.status_code == 204, archived.text

    stay = available_room["stay"]
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
