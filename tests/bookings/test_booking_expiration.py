from datetime import datetime
from uuid import uuid4

import pytest

from api.bookings import create_booking, get_booking
from api.payments import create_payment, get_payment, simulate_payment_success
from api.rooms import get_room_availability
from db import move_booking_expiry_to_past
from tests.assertions import assert_api_error


@pytest.mark.db
def test_expired_booking_cancels_payment_and_releases_room(
    database_url, base_url, stay_dates, pending_payment, user_access_token, second_user,
):
    booking = pending_payment["booking"]
    payment = pending_payment["payment"]
    stay = stay_dates
    occupied = get_room_availability(base_url, booking["room_id"], stay)
    assert occupied.status_code == 200, occupied.text
    occupied_body = occupied.json()
    assert occupied_body["room_id"] == booking["room_id"]
    assert occupied_body["available"] is False
    assert occupied_body["reason"] == "ROOM_NOT_AVAILABLE"

    expires_at = move_booking_expiry_to_past(database_url, booking["id"], booking["user_id"])
    assert expires_at < datetime.fromisoformat(booking["expires_at"])

    response = simulate_payment_success(base_url, user_access_token, payment["id"])
    assert_api_error(response, status=409, code="BOOKING_EXPIRED")

    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    expired = saved_booking.json()
    assert expired["status"] == "expired"
    assert datetime.fromisoformat(expired["expires_at"]) == expires_at
    for field in (
        "id", "user_id", "room_id", "check_in", "check_out", "guests",
        "price_per_night", "total_price", "currency",
    ):
        assert expired[field] == booking[field]

    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    cancelled_payment = saved_payment.json()
    assert cancelled_payment["status"] == "cancelled"
    for field in ("id", "booking_id", "amount", "currency", "failure_reason"):
        assert cancelled_payment[field] == payment[field]

    new_payment = create_payment(base_url, user_access_token, booking["id"])
    assert_api_error(new_payment, status=409, code="BOOKING_EXPIRED")

    availability = get_room_availability(base_url, booking["room_id"], stay)
    assert availability.status_code == 200, availability.text
    body = availability.json()
    assert body["room_id"] == booking["room_id"]
    assert body["available"] is True
    assert body["reason"] is None

    payload = {"room_id": booking["room_id"], **stay}
    created = create_booking(base_url, second_user["access_token"], payload, uuid4().hex)
    assert created.status_code == 201, created.text
    new_booking = created.json()
    assert new_booking["id"] != booking["id"]
    assert new_booking["user_id"] == second_user["id"]
    assert new_booking["status"] == "pending_payment"
    for field, value in payload.items():
        assert new_booking[field] == value
    saved_new = get_booking(base_url, second_user["access_token"], new_booking["id"])
    assert saved_new.status_code == 200, saved_new.text
    assert saved_new.json() == new_booking

    original = get_booking(base_url, user_access_token, booking["id"])
    assert original.status_code == 200, original.text
    assert original.json() == expired
