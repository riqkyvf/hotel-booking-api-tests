import pytest

from api.bookings import get_booking
from api.payments import (
    create_payment,
    get_payment,
    simulate_payment_failure,
    simulate_payment_success,
)
from api.rooms import get_room_availability
from data.payments import PAYMENT_DECLINE_REASON, PAYMENT_FAILURE_CASES


@pytest.mark.parametrize("payload,expected_reason", PAYMENT_FAILURE_CASES)
def test_payment_failure_preserves_booking_and_room_hold(
    base_url, stay_dates, pending_payment, user_access_token, payload, expected_reason,
):
    booking = pending_payment["booking"]
    payment = pending_payment["payment"]

    response = simulate_payment_failure(base_url, user_access_token, payment["id"], payload)
    assert response.status_code == 200, response.text
    failed = response.json()
    assert failed["status"] == "failed"
    assert failed["failure_reason"] == expected_reason
    assert response.headers.get("X-Request-ID")
    for field in ("id", "booking_id", "amount", "currency"):
        assert failed[field] == payment[field]

    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == failed

    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    body = saved_booking.json()
    assert body["status"] == "pending_payment"
    for field in (
        "id", "user_id", "room_id", "check_in", "check_out", "guests",
        "price_per_night", "total_price", "currency", "expires_at",
    ):
        assert body[field] == booking[field]

    availability = get_room_availability(base_url, booking["room_id"], stay_dates)
    assert availability.status_code == 200, availability.text
    room = availability.json()
    assert room["room_id"] == booking["room_id"]
    assert room["available"] is False
    assert room["reason"] == "ROOM_NOT_AVAILABLE"


def test_user_can_pay_with_new_payment_after_failure(
    base_url, pending_payment, user_access_token,
):
    booking = pending_payment["booking"]
    payment = pending_payment["payment"]
    response = simulate_payment_failure(
        base_url, user_access_token, payment["id"], {"reason": PAYMENT_DECLINE_REASON},
    )
    assert response.status_code == 200, response.text
    failed = response.json()
    assert failed["status"] == "failed"
    assert failed["failure_reason"] == PAYMENT_DECLINE_REASON

    created = create_payment(base_url, user_access_token, booking["id"])
    assert created.status_code == 201, created.text
    new_payment = created.json()
    assert new_payment["id"] != payment["id"]
    assert new_payment["booking_id"] == booking["id"]
    assert new_payment["status"] == "pending"
    assert new_payment["failure_reason"] is None
    assert new_payment["amount"] == booking["total_price"]
    assert new_payment["currency"] == booking["currency"]

    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    pending_booking = saved_booking.json()
    assert pending_booking["status"] == "pending_payment"
    assert pending_booking["expires_at"] == booking["expires_at"]

    succeeded = simulate_payment_success(base_url, user_access_token, new_payment["id"])
    assert succeeded.status_code == 200, succeeded.text
    paid = succeeded.json()
    assert paid["status"] == "succeeded"
    assert paid["failure_reason"] is None
    for field in ("id", "booking_id", "amount", "currency"):
        assert paid[field] == new_payment[field]

    saved_payment = get_payment(base_url, user_access_token, new_payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == paid

    confirmed = get_booking(base_url, user_access_token, booking["id"])
    assert confirmed.status_code == 200, confirmed.text
    confirmed_booking = confirmed.json()
    assert confirmed_booking["status"] == "confirmed"
    for field in (
        "id", "user_id", "room_id", "check_in", "check_out", "guests",
        "price_per_night", "total_price", "currency", "expires_at",
    ):
        assert confirmed_booking[field] == booking[field]

    old_payment = get_payment(base_url, user_access_token, payment["id"])
    assert old_payment.status_code == 200, old_payment.text
    assert old_payment.json() == failed
