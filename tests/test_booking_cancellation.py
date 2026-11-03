from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from jsonschema import validate

from api.bookings import cancel_booking, create_booking, get_booking
from api.payments import create_payment, get_payment, simulate_payment_success
from api.rooms import get_room_availability
from data.booking import BLOCKING_BOOKING_STATUSES, BOOKING_NIGHTS, CANCELLATION_PAYMENT_CASES
from schemas.error_response import ERROR_SCHEMA


@pytest.fixture
def booking_to_cancel(base_url, available_room, user_access_token, payment_status):
    payload = {"room_id": available_room["room"]["id"], **available_room["stay"]}
    created = create_booking(base_url, user_access_token, payload, uuid4().hex)
    assert created.status_code == 201, created.text
    booking = created.json()
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

    saved = get_booking(base_url, user_access_token, booking["id"])
    assert saved.status_code == 200, saved.text
    original = saved.json()
    expected_status = "confirmed" if payment_status == "succeeded" else "pending_payment"
    assert original["status"] == expected_status
    for field, value in payload.items():
        assert original[field] == value
    return {"booking": original, "payment": payment}


@pytest.mark.parametrize("payment_status,expected_payment_status", CANCELLATION_PAYMENT_CASES)
def test_cancellation_releases_room_for_another_user(
    base_url, available_room, booking_to_cancel, user_access_token, second_user,
    payment_status, expected_payment_status,
):
    booking = booking_to_cancel["booking"]
    room_id = booking["room_id"]
    stay = available_room["stay"]

    occupied = get_room_availability(base_url, room_id, stay)
    assert occupied.status_code == 200, occupied.text
    occupied_body = occupied.json()
    assert occupied_body["room_id"] == room_id
    assert occupied_body["available"] is False
    assert occupied_body["reason"] == "ROOM_NOT_AVAILABLE"

    response = cancel_booking(base_url, user_access_token, booking["id"])
    assert response.status_code == 200, response.text
    cancelled = response.json()
    assert cancelled["status"] == "cancelled"
    assert response.headers.get("X-Request-ID")
    for field in (
        "id", "user_id", "room_id", "check_in", "check_out", "guests",
        "price_per_night", "total_price", "currency",
    ):
        assert cancelled[field] == booking[field]

    saved = get_booking(base_url, user_access_token, booking["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == cancelled

    payment = booking_to_cancel["payment"]
    if payment is not None:
        saved_payment = get_payment(base_url, user_access_token, payment["id"])
        assert saved_payment.status_code == 200, saved_payment.text
        payment_body = saved_payment.json()
        assert payment_body["status"] == expected_payment_status
        for field in ("id", "booking_id", "amount", "currency"):
            assert payment_body[field] == payment[field]

    availability = get_room_availability(base_url, room_id, stay)
    assert availability.status_code == 200, availability.text
    body = availability.json()
    assert body["room_id"] == room_id
    assert body["available"] is True
    assert body["reason"] is None
    for field, value in stay.items():
        assert body[field] == value

    payload = {"room_id": room_id, **stay}
    created = create_booking(base_url, second_user["token"], payload, uuid4().hex)
    assert created.status_code == 201, created.text
    new_booking = created.json()
    assert new_booking["id"] != booking["id"]
    assert new_booking["user_id"] == second_user["id"]
    assert new_booking["status"] == "pending_payment"
    for field, value in payload.items():
        assert new_booking[field] == value

    saved_new = get_booking(base_url, second_user["token"], new_booking["id"])
    assert saved_new.status_code == 200, saved_new.text
    assert saved_new.json() == new_booking

    original = get_booking(base_url, user_access_token, booking["id"])
    assert original.status_code == 200, original.text
    assert original.json() == cancelled


@pytest.mark.parametrize("payment_status,expected_payment_status", CANCELLATION_PAYMENT_CASES)
def test_repeated_cancellation_preserves_booking_and_payment(
    base_url, available_room, booking_to_cancel, user_access_token,
    payment_status, expected_payment_status,
):
    booking = booking_to_cancel["booking"]
    payment = booking_to_cancel["payment"]
    first = cancel_booking(base_url, user_access_token, booking["id"])
    assert first.status_code == 200, first.text
    cancelled = first.json()
    assert cancelled["status"] == "cancelled"
    for field in (
        "id", "user_id", "room_id", "check_in", "check_out", "guests",
        "price_per_night", "total_price", "currency",
    ):
        assert cancelled[field] == booking[field]

    cancelled_payment = None
    if payment is not None:
        after_first = get_payment(base_url, user_access_token, payment["id"])
        assert after_first.status_code == 200, after_first.text
        cancelled_payment = after_first.json()
        assert cancelled_payment["status"] == expected_payment_status
        for field in ("id", "booking_id", "amount", "currency"):
            assert cancelled_payment[field] == payment[field]

    response = cancel_booking(base_url, user_access_token, booking["id"])
    assert response.status_code == 200, response.text
    assert response.json() == cancelled
    assert response.headers.get("X-Request-ID")

    saved = get_booking(base_url, user_access_token, booking["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == cancelled
    if payment is not None:
        saved_payment = get_payment(base_url, user_access_token, payment["id"])
        assert saved_payment.status_code == 200, saved_payment.text
        assert saved_payment.json() == cancelled_payment

    availability = get_room_availability(base_url, booking["room_id"], available_room["stay"])
    assert availability.status_code == 200, availability.text
    body = availability.json()
    assert body["room_id"] == booking["room_id"]
    assert body["available"] is True
    assert body["reason"] is None


@pytest.mark.parametrize("booking_status", BLOCKING_BOOKING_STATUSES)
def test_cancellation_on_check_in_day_is_rejected(
    base_url, available_room, user_access_token, booking_status,
):
    check_in = datetime.now(timezone.utc).date()
    stay = {
        "check_in": check_in.isoformat(),
        "check_out": (check_in + timedelta(days=BOOKING_NIGHTS)).isoformat(),
        "guests": available_room["stay"]["guests"],
    }
    payload = {"room_id": available_room["room"]["id"], **stay}
    created = create_booking(base_url, user_access_token, payload, uuid4().hex)
    assert created.status_code == 201, created.text
    booking = created.json()
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

    response = cancel_booking(base_url, user_access_token, booking["id"])
    assert response.status_code == 409, response.text
    body = response.json()
    validate(instance=body, schema=ERROR_SCHEMA)
    assert body["error"]["code"] == "CANCELLATION_CLOSED"
    assert response.headers.get("X-Request-ID")
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]

    saved = get_booking(base_url, user_access_token, booking["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == original_booking
    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == original_payment

    availability = get_room_availability(base_url, booking["room_id"], stay)
    assert availability.status_code == 200, availability.text
    unavailable = availability.json()
    assert unavailable["room_id"] == booking["room_id"]
    assert unavailable["available"] is False
    assert unavailable["reason"] == "ROOM_NOT_AVAILABLE"
