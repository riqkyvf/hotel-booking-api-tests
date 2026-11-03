from uuid import uuid4

from jsonschema import validate

from api.bookings import cancel_booking, create_booking, get_booking, list_bookings
from api.payments import (
    create_payment, get_payment, simulate_payment_failure, simulate_payment_success,
)
from api.rooms import get_room_availability
from data.payments import PAYMENT_DECLINE_REASON
from schemas.error_response import ERROR_SCHEMA


def test_user_cannot_read_another_users_booking(
    base_url, private_booking, second_user, user_access_token,
):
    booking = private_booking["booking"]
    assert second_user["id"] != booking["user_id"]

    response = get_booking(base_url, second_user["token"], booking["id"])
    assert response.status_code == 404, response.text
    body = response.json()
    validate(instance=body, schema=ERROR_SCHEMA)
    assert body["error"]["code"] == "NOT_FOUND"
    assert response.headers.get("X-Request-ID")
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]

    bookings = list_bookings(base_url, second_user["token"])
    assert bookings.status_code == 200, bookings.text
    page = bookings.json()
    assert page["total"] == 0
    assert page["items"] == []

    saved = get_booking(base_url, user_access_token, booking["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == booking


def test_user_cannot_cancel_another_users_booking(
    base_url, available_room, private_booking, second_user, user_access_token,
):
    booking = private_booking["booking"]
    payment = private_booking["payment"]
    assert second_user["id"] != booking["user_id"]

    response = cancel_booking(base_url, second_user["token"], booking["id"])
    assert response.status_code == 404, response.text
    body = response.json()
    validate(instance=body, schema=ERROR_SCHEMA)
    assert body["error"]["code"] == "NOT_FOUND"
    assert response.headers.get("X-Request-ID")
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]

    saved = get_booking(base_url, user_access_token, booking["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == booking
    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == payment

    availability = get_room_availability(base_url, booking["room_id"], available_room["stay"])
    assert availability.status_code == 200, availability.text
    availability_body = availability.json()
    assert availability_body["room_id"] == booking["room_id"]
    assert availability_body["available"] is False
    assert availability_body["reason"] == "ROOM_NOT_AVAILABLE"


def test_user_cannot_read_another_users_payment(
    base_url, private_booking, second_user, user_access_token,
):
    booking = private_booking["booking"]
    payment = private_booking["payment"]
    assert second_user["id"] != booking["user_id"]

    response = get_payment(base_url, second_user["token"], payment["id"])
    assert response.status_code == 404, response.text
    body = response.json()
    validate(instance=body, schema=ERROR_SCHEMA)
    assert body["error"]["code"] == "NOT_FOUND"
    assert response.headers.get("X-Request-ID")
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]

    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == payment
    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    assert saved_booking.json() == booking


def test_user_cannot_create_payment_for_another_users_booking(
    base_url, available_room, registered_user, second_user, user_access_token,
):
    payload = {"room_id": available_room["room"]["id"], **available_room["stay"]}
    created = create_booking(base_url, user_access_token, payload, uuid4().hex)
    assert created.status_code == 201, created.text
    booking = created.json()
    assert booking["status"] == "pending_payment"
    assert booking["user_id"] == registered_user["user"]["id"]
    assert second_user["id"] != booking["user_id"]
    for field, value in payload.items():
        assert booking[field] == value

    response = create_payment(base_url, second_user["token"], booking["id"])
    assert response.status_code == 404, response.text
    body = response.json()
    validate(instance=body, schema=ERROR_SCHEMA)
    assert body["error"]["code"] == "NOT_FOUND"
    assert response.headers.get("X-Request-ID")
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]

    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    assert saved_booking.json() == booking

    # A rejected request must not leave a pending payment that blocks the owner.
    owner_response = create_payment(base_url, user_access_token, booking["id"])
    assert owner_response.status_code == 201, owner_response.text
    payment = owner_response.json()
    assert payment["booking_id"] == booking["id"]
    assert payment["status"] == "pending"
    assert payment["failure_reason"] is None
    assert payment["amount"] == booking["total_price"]
    assert payment["currency"] == booking["currency"]
    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == payment


def test_user_cannot_simulate_success_of_another_users_payment(
    base_url, private_booking, second_user, user_access_token,
):
    booking = private_booking["booking"]
    payment = private_booking["payment"]
    assert second_user["id"] != booking["user_id"]

    response = simulate_payment_success(base_url, second_user["token"], payment["id"])
    assert response.status_code == 404, response.text
    body = response.json()
    validate(instance=body, schema=ERROR_SCHEMA)
    assert body["error"]["code"] == "NOT_FOUND"
    assert response.headers.get("X-Request-ID")
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]

    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == payment
    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    assert saved_booking.json() == booking


def test_user_cannot_simulate_failure_of_another_users_payment(
    base_url, private_booking, second_user, user_access_token,
):
    booking = private_booking["booking"]
    payment = private_booking["payment"]
    assert second_user["id"] != booking["user_id"]

    response = simulate_payment_failure(
        base_url, second_user["token"], payment["id"], {"reason": PAYMENT_DECLINE_REASON},
    )
    assert response.status_code == 404, response.text
    body = response.json()
    validate(instance=body, schema=ERROR_SCHEMA)
    assert body["error"]["code"] == "NOT_FOUND"
    assert response.headers.get("X-Request-ID")
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]

    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == payment
    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    assert saved_booking.json() == booking
