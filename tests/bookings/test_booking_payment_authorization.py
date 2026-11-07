from uuid import uuid4

import pytest

from api.bookings import cancel_booking, create_booking, get_booking, list_bookings
from api.payments import create_payment, get_payment, simulate_payment_failure, simulate_payment_success
from api.rooms import get_room_availability
from tests.assertions import assert_api_error


def assert_missing_authorization(response, token):
    assert_api_error(response, status=401, code="UNAUTHORIZED")
    assert response.headers.get("WWW-Authenticate") == "Bearer"
    # Ensure the two cases really send different HTTP headers.
    if token is None:
        assert "Authorization" not in response.request.headers
    else:
        assert response.request.headers["Authorization"] == "Bearer "


@pytest.mark.parametrize("token", [None, ""], ids=["no_header", "empty_bearer"])
def test_create_booking_requires_authorization(
    base_url, available_room, stay_dates, user_access_token, token,
):
    payload = {"room_id": available_room["room"]["id"], **stay_dates}
    key = uuid4().hex
    response = create_booking(base_url, token, payload, key)
    assert_missing_authorization(response, token)

    bookings = list_bookings(base_url, user_access_token)
    assert bookings.status_code == 200, bookings.text
    assert bookings.json()["total"] == 0
    assert bookings.json()["items"] == []
    availability = get_room_availability(base_url, payload["room_id"], stay_dates)
    assert availability.status_code == 200, availability.text
    assert availability.json()["available"] is True
    assert availability.json()["reason"] is None

    # Valid retry proves that rejection did not reserve the room or consume this key.
    created = create_booking(base_url, user_access_token, payload, key)
    assert created.status_code == 201, created.text
    assert created.headers.get("Idempotency-Replayed", "").lower() == "false"
    bookings = list_bookings(base_url, user_access_token)
    assert bookings.status_code == 200, bookings.text
    assert bookings.json()["total"] == 1
    assert [item["id"] for item in bookings.json()["items"]] == [created.json()["id"]]


@pytest.mark.parametrize("token", [None, ""], ids=["no_header", "empty_bearer"])
def test_create_payment_requires_authorization(
    base_url, available_room, stay_dates, user_access_token, token,
):
    created_booking = create_booking(base_url, user_access_token,
                                     {"room_id": available_room["room"]["id"], **stay_dates}, uuid4().hex)
    assert created_booking.status_code == 201, created_booking.text
    booking = created_booking.json()
    response = create_payment(base_url, token, booking["id"])
    assert_missing_authorization(response, token)
    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    assert saved_booking.json() == booking

    # No existing pending payment: a premature 409 cannot hide missing authorization.
    created_payment = create_payment(base_url, user_access_token, booking["id"])
    assert created_payment.status_code == 201, created_payment.text
    payment = created_payment.json()
    assert payment["booking_id"] == booking["id"]
    assert payment["status"] == "pending"
    assert payment["amount"] == booking["total_price"]
    assert payment["currency"] == booking["currency"]
    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == payment


@pytest.mark.parametrize("token", [None, ""], ids=["no_header", "empty_bearer"])
@pytest.mark.parametrize("operation", ["read_booking", "cancel_booking", "read_payment", "success", "failure"])
def test_existing_booking_and_payment_require_authorization(
    base_url, pending_payment, user_access_token, token, operation,
):
    booking = pending_payment["booking"]
    payment = pending_payment["payment"]
    if operation == "read_booking":
        response = get_booking(base_url, token, booking["id"])
    elif operation == "cancel_booking":
        response = cancel_booking(base_url, token, booking["id"])
    elif operation == "read_payment":
        response = get_payment(base_url, token, payment["id"])
    elif operation == "success":
        response = simulate_payment_success(base_url, token, payment["id"])
    else:
        response = simulate_payment_failure(base_url, token, payment["id"], {"reason": "Must Not Save"})
    assert_missing_authorization(response, token)

    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    assert saved_booking.json() == booking
    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == payment
