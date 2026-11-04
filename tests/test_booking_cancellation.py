from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from api.bookings import cancel_booking, create_booking, get_booking
from api.payments import create_payment, get_payment, simulate_payment_success
from api.rooms import get_room_availability
from data.booking import BLOCKING_BOOKING_STATUSES, BOOKING_NIGHTS, CANCELLATION_PAYMENT_CASES
from tests.assertions import assert_api_error


@pytest.fixture
def booking_to_cancel(base_url, available_room, stay_dates, user_access_token, payment_status):
    """Return current {booking, payment}; payment is None when no payment was requested."""
    payload = {"room_id": available_room["room"]["id"], **stay_dates}
    booking_response = create_booking(base_url, user_access_token, payload, uuid4().hex)
    assert booking_response.status_code == 201, booking_response.text
    booking = booking_response.json()
    assert booking["status"] == "pending_payment"

    payment = None
    if payment_status is not None:
        created_payment = create_payment(base_url, user_access_token, booking["id"])
        assert created_payment.status_code == 201, created_payment.text
        payment = created_payment.json()
        assert payment["status"] == "pending"
        assert payment["booking_id"] == booking["id"]
        assert payment["amount"] == booking["total_price"]
        assert payment["currency"] == booking["currency"]

    if payment_status == "succeeded":
        succeeded = simulate_payment_success(base_url, user_access_token, payment["id"])
        assert succeeded.status_code == 200, succeeded.text
        assert succeeded.json()["status"] == "succeeded"

    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    current_booking = saved_booking.json()
    expected_status = "confirmed" if payment_status == "succeeded" else "pending_payment"
    assert current_booking["status"] == expected_status
    for field, value in payload.items():
        assert current_booking[field] == value
    if payment is not None:
        saved_payment = get_payment(base_url, user_access_token, payment["id"])
        assert saved_payment.status_code == 200, saved_payment.text
        current_payment = saved_payment.json()
        assert current_payment["status"] == payment_status
        for field in ("id", "booking_id", "amount", "currency"):
            assert current_payment[field] == payment[field]
        payment = current_payment

    return {"booking": current_booking, "payment": payment}


@pytest.mark.parametrize("payment_status,expected_payment_status", CANCELLATION_PAYMENT_CASES)
@pytest.mark.smoke
def test_cancellation_releases_room_for_another_user(
    base_url, stay_dates, booking_to_cancel, user_access_token, second_user,
    payment_status, expected_payment_status,
):
    booking = booking_to_cancel["booking"]
    room_id = booking["room_id"]
    stay = stay_dates

    # The existing booking must hold the room before cancellation.
    occupied_response = get_room_availability(base_url, room_id, stay)
    assert occupied_response.status_code == 200, occupied_response.text
    occupied_body = occupied_response.json()
    assert occupied_body["room_id"] == room_id
    assert occupied_body["available"] is False
    assert occupied_body["reason"] == "ROOM_NOT_AVAILABLE"

    # Cancellation must persist and update the associated payment.
    cancel_response = cancel_booking(base_url, user_access_token, booking["id"])
    assert cancel_response.status_code == 200, cancel_response.text
    cancelled_booking = cancel_response.json()
    assert cancelled_booking["status"] == "cancelled"
    assert cancel_response.headers.get("X-Request-ID")
    for field in (
        "id", "user_id", "room_id", "check_in", "check_out", "guests",
        "price_per_night", "total_price", "currency",
    ):
        assert cancelled_booking[field] == booking[field]

    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    assert saved_booking.json() == cancelled_booking

    payment = booking_to_cancel["payment"]
    if payment is not None:
        saved_payment = get_payment(base_url, user_access_token, payment["id"])
        assert saved_payment.status_code == 200, saved_payment.text
        payment_body = saved_payment.json()
        assert payment_body["status"] == expected_payment_status
        for field in ("id", "booking_id", "amount", "currency"):
            assert payment_body[field] == payment[field]

    # Released dates must be available for another user.
    availability = get_room_availability(base_url, room_id, stay)
    assert availability.status_code == 200, availability.text
    availability_body = availability.json()
    assert availability_body["room_id"] == room_id
    assert availability_body["available"] is True
    assert availability_body["reason"] is None
    for field, value in stay.items():
        assert availability_body[field] == value

    payload = {"room_id": room_id, **stay}
    new_booking_response = create_booking(base_url, second_user["access_token"], payload, uuid4().hex)
    assert new_booking_response.status_code == 201, new_booking_response.text
    new_booking = new_booking_response.json()
    assert new_booking["id"] != booking["id"]
    assert new_booking["user_id"] == second_user["id"]
    assert new_booking["status"] == "pending_payment"
    for field, value in payload.items():
        assert new_booking[field] == value

    saved_new_booking = get_booking(base_url, second_user["access_token"], new_booking["id"])
    assert saved_new_booking.status_code == 200, saved_new_booking.text
    assert saved_new_booking.json() == new_booking

    # A new booking must not change the cancelled booking.
    original_booking_response = get_booking(base_url, user_access_token, booking["id"])
    assert original_booking_response.status_code == 200, original_booking_response.text
    assert original_booking_response.json() == cancelled_booking


@pytest.mark.parametrize("payment_status,expected_payment_status", CANCELLATION_PAYMENT_CASES)
def test_repeated_cancellation_preserves_booking_and_payment(
    base_url, stay_dates, booking_to_cancel, user_access_token,
    payment_status, expected_payment_status,
):
    booking = booking_to_cancel["booking"]
    payment = booking_to_cancel["payment"]
    first_cancel_response = cancel_booking(base_url, user_access_token, booking["id"])
    assert first_cancel_response.status_code == 200, first_cancel_response.text
    cancelled_booking = first_cancel_response.json()
    assert cancelled_booking["status"] == "cancelled"
    for field in (
        "id", "user_id", "room_id", "check_in", "check_out", "guests",
        "price_per_night", "total_price", "currency",
    ):
        assert cancelled_booking[field] == booking[field]

    cancelled_payment = None
    if payment is not None:
        payment_after_first_cancel = get_payment(base_url, user_access_token, payment["id"])
        assert payment_after_first_cancel.status_code == 200, payment_after_first_cancel.text
        cancelled_payment = payment_after_first_cancel.json()
        assert cancelled_payment["status"] == expected_payment_status
        for field in ("id", "booking_id", "amount", "currency"):
            assert cancelled_payment[field] == payment[field]

    # Repeating cancellation must preserve both final snapshots.
    repeated_cancel_response = cancel_booking(base_url, user_access_token, booking["id"])
    assert repeated_cancel_response.status_code == 200, repeated_cancel_response.text
    assert repeated_cancel_response.json() == cancelled_booking
    assert repeated_cancel_response.headers.get("X-Request-ID")

    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    assert saved_booking.json() == cancelled_booking
    if payment is not None:
        saved_payment = get_payment(base_url, user_access_token, payment["id"])
        assert saved_payment.status_code == 200, saved_payment.text
        assert saved_payment.json() == cancelled_payment

    availability = get_room_availability(base_url, booking["room_id"], stay_dates)
    assert availability.status_code == 200, availability.text
    availability_body = availability.json()
    assert availability_body["room_id"] == booking["room_id"]
    assert availability_body["available"] is True
    assert availability_body["reason"] is None


@pytest.mark.parametrize("booking_status", BLOCKING_BOOKING_STATUSES)
def test_cancellation_on_check_in_day_is_rejected(
    base_url, available_room, stay_dates, user_access_token, booking_status,
):
    check_in = datetime.now(timezone.utc).date()
    stay = {
        "check_in": check_in.isoformat(),
        "check_out": (check_in + timedelta(days=BOOKING_NIGHTS)).isoformat(),
        "guests": stay_dates["guests"],
    }
    payload = {"room_id": available_room["room"]["id"], **stay}
    booking_response = create_booking(base_url, user_access_token, payload, uuid4().hex)
    assert booking_response.status_code == 201, booking_response.text
    booking = booking_response.json()
    assert booking["status"] == "pending_payment"
    for field, value in payload.items():
        assert booking[field] == value

    created_payment = create_payment(base_url, user_access_token, booking["id"])
    assert created_payment.status_code == 201, created_payment.text
    payment = created_payment.json()
    assert payment["status"] == "pending"
    assert payment["booking_id"] == booking["id"]
    assert payment["amount"] == booking["total_price"]
    assert payment["currency"] == booking["currency"]
    if booking_status == "confirmed":
        succeeded = simulate_payment_success(base_url, user_access_token, payment["id"])
        assert succeeded.status_code == 200, succeeded.text
        assert succeeded.json()["status"] == "succeeded"

    # Capture both resources before the rejected cancellation.
    before_booking = get_booking(base_url, user_access_token, booking["id"])
    assert before_booking.status_code == 200, before_booking.text
    original_booking = before_booking.json()
    assert original_booking["id"] == booking["id"]
    assert original_booking["status"] == booking_status
    before_payment = get_payment(base_url, user_access_token, payment["id"])
    assert before_payment.status_code == 200, before_payment.text
    original_payment = before_payment.json()
    assert original_payment["id"] == payment["id"]
    expected_status = "succeeded" if booking_status == "confirmed" else "pending"
    assert original_payment["status"] == expected_status

    cancel_response = cancel_booking(base_url, user_access_token, booking["id"])
    assert_api_error(cancel_response, status=409, code="CANCELLATION_CLOSED")

    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    assert saved_booking.json() == original_booking
    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == original_payment

    availability = get_room_availability(base_url, booking["room_id"], stay)
    assert availability.status_code == 200, availability.text
    availability_body = availability.json()
    assert availability_body["room_id"] == booking["room_id"]
    assert availability_body["available"] is False
    assert availability_body["reason"] == "ROOM_NOT_AVAILABLE"
