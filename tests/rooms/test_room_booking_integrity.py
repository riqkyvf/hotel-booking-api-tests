from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from api.bookings import create_booking, get_booking
from api.payments import get_payment, simulate_payment_success
from api.rooms import archive_room, get_room, update_room, update_room_availability
from tests.assertions import assert_api_error


ROOM_INPUT_FIELDS = ("room_number", "type", "capacity", "price_per_night")


def test_capacity_cannot_be_reduced_below_existing_booking_guests(
    base_url, available_room, booking_with_payment, user_access_token, admin_access_token,
):
    room = available_room["room"]
    booking = booking_with_payment["booking"]
    payment = booking_with_payment["payment"]
    assert 1 < booking["guests"] <= room["capacity"]
    payload = {field: room[field] for field in ROOM_INPUT_FIELDS}
    payload["capacity"] = booking["guests"] - 1

    response = update_room(base_url, admin_access_token, room["id"], payload)
    assert_api_error(response, status=409, code="CAPACITY_IN_USE")

    saved_room = get_room(base_url, room["id"])
    assert saved_room.status_code == 200, saved_room.text
    assert saved_room.json() == room
    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    assert saved_booking.json() == booking
    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == payment


def test_room_with_active_booking_cannot_be_archived(
    base_url, available_room, booking_with_payment, user_access_token, admin_access_token,
):
    room = available_room["room"]
    booking = booking_with_payment["booking"]
    payment = booking_with_payment["payment"]

    response = archive_room(base_url, admin_access_token, room["id"])
    assert_api_error(response, status=409, code="ACTIVE_BOOKINGS_EXIST")

    saved_room = get_room(base_url, room["id"])
    assert saved_room.status_code == 200, saved_room.text
    assert saved_room.json() == room
    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    assert saved_booking.json() == booking
    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == payment


def test_room_price_change_affects_only_new_bookings(
    base_url, available_room, pending_payment, user_access_token, admin_access_token, second_user,
):
    room = available_room["room"]
    booking = pending_payment["booking"]
    payment = pending_payment["payment"]
    new_price = "2345.67"
    assert Decimal(new_price) != Decimal(room["price_per_night"])
    payload = {field: room[field] for field in ROOM_INPUT_FIELDS}
    payload["price_per_night"] = new_price

    updated = update_room(base_url, admin_access_token, room["id"], payload)
    assert updated.status_code == 200, updated.text
    updated_room = updated.json()
    assert updated_room["id"] == room["id"]
    assert updated_room["price_per_night"] == new_price
    for field in ("hotel_id", "room_number", "type", "capacity", "is_available", "is_archived"):
        assert updated_room[field] == room[field]
    saved_room = get_room(base_url, room["id"])
    assert saved_room.status_code == 200, saved_room.text
    assert saved_room.json() == updated_room

    # Existing booking and payment retain their original monetary snapshots.
    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    assert saved_booking.json() == booking
    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == payment

    # A separate, non-overlapping stay must use the newly saved room price.
    nights = (date.fromisoformat(booking["check_out"]) - date.fromisoformat(booking["check_in"])).days
    check_in = date.fromisoformat(booking["check_out"]) + timedelta(days=1)
    new_payload = {
        "room_id": room["id"],
        "check_in": check_in.isoformat(),
        "check_out": (check_in + timedelta(days=nights)).isoformat(),
        "guests": booking["guests"],
    }
    created = create_booking(base_url, second_user["access_token"], new_payload, uuid4().hex)
    assert created.status_code == 201, created.text
    new_booking = created.json()
    assert new_booking["id"] != booking["id"]
    assert new_booking["user_id"] == second_user["id"]
    assert new_booking["status"] == "pending_payment"
    for field, value in new_payload.items():
        assert new_booking[field] == value
    assert new_booking["price_per_night"] == new_price
    assert Decimal(new_booking["total_price"]) == Decimal(new_price) * nights
    assert new_booking["currency"] == booking["currency"]
    saved_new_booking = get_booking(base_url, second_user["access_token"], new_booking["id"])
    assert saved_new_booking.status_code == 200, saved_new_booking.text
    assert saved_new_booking.json() == new_booking


def test_existing_booking_can_be_paid_after_room_is_disabled(
    base_url, available_room, pending_payment, user_access_token, admin_access_token,
):
    room = available_room["room"]
    booking = pending_payment["booking"]
    payment = pending_payment["payment"]

    disabled = update_room_availability(base_url, admin_access_token, room["id"], {"is_available": False})
    assert disabled.status_code == 200, disabled.text
    disabled_room = disabled.json()
    assert disabled_room["id"] == room["id"]
    assert disabled_room["is_available"] is False
    for field in ("hotel_id", "room_number", "type", "capacity", "price_per_night", "is_archived"):
        assert disabled_room[field] == room[field]

    paid = simulate_payment_success(base_url, user_access_token, payment["id"])
    assert paid.status_code == 200, paid.text
    paid_payment = paid.json()
    assert paid_payment["status"] == "succeeded"
    for field in ("id", "booking_id", "amount", "currency", "failure_reason"):
        assert paid_payment[field] == payment[field]
    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == paid_payment

    confirmed = get_booking(base_url, user_access_token, booking["id"])
    assert confirmed.status_code == 200, confirmed.text
    confirmed_booking = confirmed.json()
    assert confirmed_booking["status"] == "confirmed"
    for field in (
        "id", "user_id", "room_id", "check_in", "check_out", "guests",
        "price_per_night", "total_price", "currency", "expires_at",
    ):
        assert confirmed_booking[field] == booking[field]
    saved_room = get_room(base_url, room["id"])
    assert saved_room.status_code == 200, saved_room.text
    assert saved_room.json() == disabled_room
