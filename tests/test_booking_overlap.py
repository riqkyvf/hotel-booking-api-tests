from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from api.bookings import create_booking, get_booking, list_bookings
from api.payments import create_payment, simulate_payment_success
from api.rooms import create_room, get_room_availability
from data.booking import (
    ADJACENT_STAYS,
    BLOCKING_BOOKING_STATUSES,
    BOOKING_ROOM_DATA,
    BOOKING_GUESTS,
    OVERLAP_CHECK_IN_OFFSET_DAYS,
    OVERLAP_NIGHTS,
    OVERLAPPING_STAYS,
)
from tests.assertions import assert_api_error


@pytest.fixture
def overlap_stay():
    check_in = datetime.now(timezone.utc).date() + timedelta(days=OVERLAP_CHECK_IN_OFFSET_DAYS)
    return {
        "check_in": check_in.isoformat(),
        "check_out": (check_in + timedelta(days=OVERLAP_NIGHTS)).isoformat(),
        "guests": BOOKING_GUESTS,
    }


@pytest.fixture(params=BLOCKING_BOOKING_STATUSES)
def blocking_booking(base_url, available_room, overlap_stay, user_access_token, request):
    payload = {"room_id": available_room["room"]["id"], **overlap_stay}
    created = create_booking(base_url, user_access_token, payload, uuid4().hex)
    assert created.status_code == 201, created.text
    booking = created.json()
    assert booking["status"] == "pending_payment"

    if request.param == "confirmed":
        paid = create_payment(base_url, user_access_token, booking["id"])
        assert paid.status_code == 201, paid.text
        payment = paid.json()
        succeeded = simulate_payment_success(base_url, user_access_token, payment["id"])
        assert succeeded.status_code == 200, succeeded.text
        assert succeeded.json()["status"] == "succeeded"

    saved = get_booking(base_url, user_access_token, booking["id"])
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["status"] == request.param
    for field, value in payload.items():
        assert body[field] == value
    return body


@pytest.mark.parametrize("start_offset,end_offset", OVERLAPPING_STAYS)
def test_overlapping_booking_is_rejected(
    base_url, available_room, overlap_stay, blocking_booking, second_user, user_access_token,
    start_offset, end_offset,
):
    check_in = date.fromisoformat(blocking_booking["check_in"])
    stay = {
        "check_in": (check_in + timedelta(days=start_offset)).isoformat(),
        "check_out": (check_in + timedelta(days=end_offset)).isoformat(),
        "guests": overlap_stay["guests"],
    }
    room_id = available_room["room"]["id"]
    availability = get_room_availability(base_url, room_id, stay)
    assert availability.status_code == 200, availability.text
    body = availability.json()
    assert body["room_id"] == room_id
    assert body["available"] is False
    assert body["reason"] == "ROOM_NOT_AVAILABLE"

    response = create_booking(
        base_url, second_user["access_token"], {"room_id": room_id, **stay}, uuid4().hex
    )
    assert_api_error(response, status=409, code="ROOM_NOT_AVAILABLE")

    bookings = list_bookings(base_url, second_user["access_token"])
    assert bookings.status_code == 200, bookings.text
    page = bookings.json()
    assert page["total"] == 0
    assert page["items"] == []

    original = get_booking(base_url, user_access_token, blocking_booking["id"])
    assert original.status_code == 200, original.text
    assert original.json() == blocking_booking


@pytest.mark.parametrize("start_offset,end_offset", ADJACENT_STAYS)
def test_adjacent_booking_is_allowed(
    base_url, available_room, overlap_stay, blocking_booking, second_user, user_access_token,
    start_offset, end_offset,
):
    check_in = date.fromisoformat(blocking_booking["check_in"])
    stay = {
        "check_in": (check_in + timedelta(days=start_offset)).isoformat(),
        "check_out": (check_in + timedelta(days=end_offset)).isoformat(),
        "guests": overlap_stay["guests"],
    }
    room_id = available_room["room"]["id"]
    availability = get_room_availability(base_url, room_id, stay)
    assert availability.status_code == 200, availability.text
    body = availability.json()
    assert body["room_id"] == room_id
    assert body["available"] is True
    assert body["reason"] is None

    payload = {"room_id": room_id, **stay}
    response = create_booking(base_url, second_user["access_token"], payload, uuid4().hex)
    assert response.status_code == 201, response.text
    booking = response.json()
    assert booking["id"] != blocking_booking["id"]
    assert booking["user_id"] == second_user["id"]
    assert booking["status"] == "pending_payment"
    for field, value in payload.items():
        assert booking[field] == value

    saved = get_booking(base_url, second_user["access_token"], booking["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == booking
    original = get_booking(base_url, user_access_token, blocking_booking["id"])
    assert original.status_code == 200, original.text
    assert original.json() == blocking_booking


def test_booking_another_room_on_same_dates_is_allowed(
    base_url, available_room, overlap_stay, blocking_booking, second_user,
    user_access_token, admin_access_token,
):
    created_room = create_room(
        base_url, admin_access_token, available_room["hotel"]["id"],
        {**BOOKING_ROOM_DATA, "room_number": "102"},
    )
    assert created_room.status_code == 201, created_room.text
    room = created_room.json()
    assert room["id"] != blocking_booking["room_id"]
    assert room["hotel_id"] == available_room["hotel"]["id"]

    stay = overlap_stay
    availability = get_room_availability(base_url, room["id"], stay)
    assert availability.status_code == 200, availability.text
    body = availability.json()
    assert body["room_id"] == room["id"]
    assert body["available"] is True
    assert body["reason"] is None

    payload = {"room_id": room["id"], **stay}
    response = create_booking(base_url, second_user["access_token"], payload, uuid4().hex)
    assert response.status_code == 201, response.text
    booking = response.json()
    assert booking["id"] != blocking_booking["id"]
    assert booking["user_id"] == second_user["id"]
    assert booking["status"] == "pending_payment"
    for field, value in payload.items():
        assert booking[field] == value

    saved = get_booking(base_url, second_user["access_token"], booking["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == booking
    original = get_booking(base_url, user_access_token, blocking_booking["id"])
    assert original.status_code == 200, original.text
    assert original.json() == blocking_booking
