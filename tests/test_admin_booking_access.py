from uuid import uuid4

from jsonschema import validate

from api.bookings import cancel_booking, create_booking, get_booking, list_bookings
from api.payments import (
    create_payment, get_payment, simulate_payment_failure, simulate_payment_success,
)
from api.rooms import get_room_availability
from data.payments import PAYMENT_DECLINE_REASON
from schemas.error_response import ERROR_SCHEMA


def test_admin_can_read_another_users_booking_and_payment(
    base_url, private_booking, user_access_token, admin_access_token,
):
    booking = private_booking["booking"]
    payment = private_booking["payment"]
    response = get_booking(base_url, admin_access_token, booking["id"])
    assert response.status_code == 200, response.text
    assert response.json() == booking
    assert response.headers.get("X-Request-ID")

    payment_response = get_payment(base_url, admin_access_token, payment["id"])
    assert payment_response.status_code == 200, payment_response.text
    assert payment_response.json() == payment

    bookings = list_bookings(base_url, admin_access_token, {"user_id": booking["user_id"]})
    assert bookings.status_code == 200, bookings.text
    page = bookings.json()
    assert page["total"] == 1
    assert [item["id"] for item in page["items"]] == [booking["id"]]

    owner_booking = get_booking(base_url, user_access_token, booking["id"])
    assert owner_booking.status_code == 200, owner_booking.text
    assert owner_booking.json() == booking
    owner_payment = get_payment(base_url, user_access_token, payment["id"])
    assert owner_payment.status_code == 200, owner_payment.text
    assert owner_payment.json() == payment


def test_admin_can_cancel_another_users_booking(
    base_url, stay_dates, private_booking, user_access_token, admin_access_token,
):
    booking = private_booking["booking"]
    payment = private_booking["payment"]
    response = cancel_booking(base_url, admin_access_token, booking["id"])
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
    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    payment_body = saved_payment.json()
    expected_status = "cancelled" if payment["status"] == "pending" else "refunded"
    assert payment_body["status"] == expected_status
    for field in ("id", "booking_id", "amount", "currency"):
        assert payment_body[field] == payment[field]

    availability = get_room_availability(base_url, booking["room_id"], stay_dates)
    assert availability.status_code == 200, availability.text
    body = availability.json()
    assert body["room_id"] == booking["room_id"]
    assert body["available"] is True
    assert body["reason"] is None


def test_admin_cannot_create_payment_for_another_users_booking(
    base_url, available_room, stay_dates, registered_user, user_access_token, admin_access_token,
):
    payload = {"room_id": available_room["room"]["id"], **stay_dates}
    created = create_booking(base_url, user_access_token, payload, uuid4().hex)
    assert created.status_code == 201, created.text
    booking = created.json()
    assert booking["status"] == "pending_payment"
    assert booking["user_id"] == registered_user["user"]["id"]
    for field, value in payload.items():
        assert booking[field] == value

    response = create_payment(base_url, admin_access_token, booking["id"])
    assert response.status_code == 404, response.text
    body = response.json()
    validate(instance=body, schema=ERROR_SCHEMA)
    assert body["error"]["code"] == "NOT_FOUND"
    assert response.headers.get("X-Request-ID")
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]

    saved = get_booking(base_url, user_access_token, booking["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == booking
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


def test_admin_cannot_simulate_success_of_another_users_payment(
    base_url, private_booking, user_access_token, admin_access_token,
):
    booking = private_booking["booking"]
    payment = private_booking["payment"]
    response = simulate_payment_success(base_url, admin_access_token, payment["id"])
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


def test_admin_cannot_simulate_failure_of_another_users_payment(
    base_url, private_booking, user_access_token, admin_access_token,
):
    booking = private_booking["booking"]
    payment = private_booking["payment"]
    response = simulate_payment_failure(
        base_url, admin_access_token, payment["id"], {"reason": PAYMENT_DECLINE_REASON},
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
