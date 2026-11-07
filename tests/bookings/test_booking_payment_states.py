import pytest

from api.bookings import cancel_booking, get_booking
from api.payments import create_payment, get_payment, simulate_payment_failure, simulate_payment_success
from db import move_booking_expiry_to_past
from tests.assertions import assert_api_error


@pytest.fixture
def non_payable_booking(base_url, pending_payment, user_access_token, request):
    """Return current booking/payment snapshots after an API-driven terminal transition."""
    booking = pending_payment["booking"]
    payment = pending_payment["payment"]
    if request.param == "confirmed":
        response = simulate_payment_success(base_url, user_access_token, payment["id"])
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "succeeded"
    elif request.param == "cancelled":
        response = cancel_booking(base_url, user_access_token, booking["id"])
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "cancelled"
    else:
        database_url = request.getfixturevalue("database_url")
        move_booking_expiry_to_past(database_url, booking["id"], booking["user_id"])
    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    assert saved_booking.json()["status"] == request.param
    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json()["status"] == ("succeeded" if request.param == "confirmed" else "cancelled")
    return {"booking": saved_booking.json(), "payment": saved_payment.json()}


@pytest.mark.parametrize("non_payable_booking", [
    "confirmed", "cancelled", pytest.param("expired", marks=pytest.mark.db),
], indirect=True)
@pytest.mark.parametrize("operation", ["create_payment", "success", "failure"])
def test_non_payable_booking_rejects_payment_operations(
    base_url, non_payable_booking, user_access_token, operation,
):
    booking = non_payable_booking["booking"]
    payment = non_payable_booking["payment"]
    if operation == "create_payment":
        response = create_payment(base_url, user_access_token, booking["id"])
    elif operation == "success":
        response = simulate_payment_success(base_url, user_access_token, payment["id"])
    else:
        response = simulate_payment_failure(base_url, user_access_token, payment["id"], {"reason": "Must not change"})
    expected_code = "BOOKING_EXPIRED" if booking["status"] == "expired" else "BOOKING_NOT_PAYABLE"
    assert_api_error(response, status=409, code=expected_code)
    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    assert saved_booking.json() == booking
    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == payment


@pytest.mark.db
@pytest.mark.parametrize("non_payable_booking", ["expired"], indirect=True)
def test_expired_booking_cannot_be_cancelled(base_url, non_payable_booking, user_access_token):
    booking = non_payable_booking["booking"]
    payment = non_payable_booking["payment"]
    response = cancel_booking(base_url, user_access_token, booking["id"])
    assert_api_error(response, status=409, code="BOOKING_STATE_CONFLICT")
    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    assert saved_booking.json() == booking
    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == payment
