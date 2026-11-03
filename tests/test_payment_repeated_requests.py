from jsonschema import validate

from api.bookings import get_booking
from api.payments import (
    create_payment,
    get_payment,
    simulate_payment_failure,
    simulate_payment_success,
)
from data.payments import PAYMENT_DECLINE_REASON
from schemas.error_response import ERROR_SCHEMA


def test_second_pending_payment_is_rejected(base_url, pending_payment, user_access_token):
    booking = pending_payment["booking"]
    payment = pending_payment["payment"]

    response = create_payment(base_url, user_access_token, booking["id"])
    assert response.status_code == 409, response.text
    body = response.json()
    validate(instance=body, schema=ERROR_SCHEMA)
    assert body["error"]["code"] == "PAYMENT_ALREADY_PENDING"
    assert response.headers.get("X-Request-ID")
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]

    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == payment
    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    assert saved_booking.json() == booking


def test_repeated_payment_success_is_rejected(base_url, pending_payment, user_access_token):
    booking = pending_payment["booking"]
    payment = pending_payment["payment"]
    succeeded = simulate_payment_success(base_url, user_access_token, payment["id"])
    assert succeeded.status_code == 200, succeeded.text
    paid = succeeded.json()
    assert paid["id"] == payment["id"]
    assert paid["status"] == "succeeded"
    confirmed_response = get_booking(base_url, user_access_token, booking["id"])
    assert confirmed_response.status_code == 200, confirmed_response.text
    confirmed = confirmed_response.json()
    assert confirmed["status"] == "confirmed"

    response = simulate_payment_success(base_url, user_access_token, payment["id"])
    assert response.status_code == 409, response.text
    body = response.json()
    validate(instance=body, schema=ERROR_SCHEMA)
    assert body["error"]["code"] == "BOOKING_NOT_PAYABLE"
    assert response.headers.get("X-Request-ID")
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]

    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == paid
    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    assert saved_booking.json() == confirmed


def test_repeated_payment_failure_preserves_original_reason(
    base_url, pending_payment, user_access_token,
):
    booking = pending_payment["booking"]
    payment = pending_payment["payment"]
    declined = simulate_payment_failure(
        base_url, user_access_token, payment["id"], {"reason": PAYMENT_DECLINE_REASON},
    )
    assert declined.status_code == 200, declined.text
    failed = declined.json()
    assert failed["id"] == payment["id"]
    assert failed["status"] == "failed"
    assert failed["failure_reason"] == PAYMENT_DECLINE_REASON

    response = simulate_payment_failure(base_url, user_access_token, payment["id"], {})
    assert response.status_code == 409, response.text
    body = response.json()
    validate(instance=body, schema=ERROR_SCHEMA)
    assert body["error"]["code"] == "PAYMENT_STATE_CONFLICT"
    assert response.headers.get("X-Request-ID")
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]

    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == failed
    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    assert saved_booking.json() == booking
