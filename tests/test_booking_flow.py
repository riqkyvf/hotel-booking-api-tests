from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from api.bookings import create_booking, get_booking, list_bookings
from api.hotels import create_hotel
from api.payments import create_payment, get_payment, simulate_payment_success
from api.rooms import create_room, get_room, get_room_availability, list_rooms
from data.booking import (
    BOOKING_CHECK_IN_OFFSET_DAYS,
    BOOKING_GUESTS,
    BOOKING_NIGHTS,
    BOOKING_ROOM_DATA,
)
from data.hotels import HOTEL_TEMPLATE


@pytest.fixture
def available_room(base_url, admin_access_token):
    hotel_response = create_hotel(
        base_url,
        admin_access_token,
        {**HOTEL_TEMPLATE, "city": f"Booking_{uuid4().hex}"},
    )
    assert hotel_response.status_code == 201, hotel_response.text
    hotel = hotel_response.json()

    room_response = create_room(base_url, admin_access_token, hotel["id"], BOOKING_ROOM_DATA)
    assert room_response.status_code == 201, room_response.text
    room = room_response.json()
    assert room["hotel_id"] == hotel["id"]
    assert room["is_available"] is True
    assert room["is_archived"] is False
    assert Decimal(room["price_per_night"]) == Decimal(BOOKING_ROOM_DATA["price_per_night"])

    check_in = datetime.now(timezone.utc).date() + timedelta(days=BOOKING_CHECK_IN_OFFSET_DAYS)
    check_out = check_in + timedelta(days=BOOKING_NIGHTS)
    stay = {
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "guests": BOOKING_GUESTS,
    }
    return {"hotel": hotel, "room": room, "stay": stay}


def test_user_can_select_available_room(base_url, available_room):
    hotel = available_room["hotel"]
    room = available_room["room"]
    stay = available_room["stay"]

    room_list = list_rooms(base_url, hotel["id"])

    assert room_list.status_code == 200, room_list.text
    assert room_list.json()["total"] == 1
    assert [item["id"] for item in room_list.json()["items"]] == [room["id"]]

    details = get_room(base_url, room["id"])

    assert details.status_code == 200, details.text
    selected = details.json()
    assert selected["id"] == room["id"]
    assert selected["hotel_id"] == hotel["id"]
    for field in ("room_number", "type", "capacity"):
        assert selected[field] == BOOKING_ROOM_DATA[field]
    assert Decimal(selected["price_per_night"]) == Decimal(BOOKING_ROOM_DATA["price_per_night"])
    assert selected["is_available"] is True
    assert selected["is_archived"] is False

    response = get_room_availability(base_url, room["id"], stay)

    assert response.status_code == 200, response.text
    availability = response.json()
    assert availability["room_id"] == room["id"]
    for field in ("check_in", "check_out", "guests"):
        assert availability[field] == stay[field]
    assert availability["available"] is True
    assert availability["reason"] is None
    assert availability["nights"] == BOOKING_NIGHTS
    assert isinstance(availability["total_price"], str)
    assert Decimal(availability["total_price"]) == (
        Decimal(BOOKING_ROOM_DATA["price_per_night"]) * BOOKING_NIGHTS
    )
    assert availability["currency"] == "RUB"


def test_user_can_create_and_read_booking(
    base_url, available_room, registered_user, user_access_token
):
    payload = {"room_id": available_room["room"]["id"], **available_room["stay"]}

    response = create_booking(base_url, user_access_token, payload, uuid4().hex)

    assert response.status_code == 201, response.text
    booking = response.json()
    UUID(booking["id"])
    assert booking["status"] == "pending_payment"
    assert booking["user_id"] == registered_user["user"]["id"]
    for field, value in payload.items():
        assert booking[field] == value
    assert isinstance(booking["price_per_night"], str)
    assert isinstance(booking["total_price"], str)
    assert Decimal(booking["price_per_night"]) == Decimal(BOOKING_ROOM_DATA["price_per_night"])
    assert Decimal(booking["total_price"]) == (
        Decimal(BOOKING_ROOM_DATA["price_per_night"]) * BOOKING_NIGHTS
    )
    assert booking["currency"] == "RUB"
    assert datetime.fromisoformat(booking["expires_at"]) > datetime.now(timezone.utc)

    saved = get_booking(base_url, user_access_token, booking["id"])

    assert saved.status_code == 200, saved.text
    for field in (
        "id", "user_id", "room_id", "check_in", "check_out", "guests",
        "status", "price_per_night", "total_price", "currency", "expires_at",
    ):
        assert saved.json()[field] == booking[field]

    bookings = list_bookings(base_url, user_access_token)

    assert bookings.status_code == 200, bookings.text
    assert bookings.json()["total"] == 1
    assert [item["id"] for item in bookings.json()["items"]] == [booking["id"]]
    assert bookings.json()["items"][0]["status"] == "pending_payment"


def test_user_can_pay_for_booking(base_url, available_room, user_access_token):
    payload = {"room_id": available_room["room"]["id"], **available_room["stay"]}
    booked = create_booking(base_url, user_access_token, payload, uuid4().hex)

    assert booked.status_code == 201, booked.text
    booking = booked.json()
    assert booking["status"] == "pending_payment"
    expected_total = Decimal(BOOKING_ROOM_DATA["price_per_night"]) * BOOKING_NIGHTS
    assert Decimal(booking["total_price"]) == expected_total

    created = create_payment(base_url, user_access_token, booking["id"])

    assert created.status_code == 201, created.text
    payment = created.json()
    UUID(payment["id"])
    assert payment["booking_id"] == booking["id"]
    assert payment["status"] == "pending"
    assert isinstance(payment["amount"], str)
    assert Decimal(payment["amount"]) == expected_total
    assert payment["currency"] == booking["currency"] == "RUB"
    assert payment["failure_reason"] is None

    pending = get_payment(base_url, user_access_token, payment["id"])
    assert pending.status_code == 200, pending.text
    for field in ("id", "booking_id", "status", "amount", "currency", "failure_reason"):
        assert pending.json()[field] == payment[field]

    response = simulate_payment_success(base_url, user_access_token, payment["id"])

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "succeeded"
    for field in ("id", "booking_id", "amount", "currency", "failure_reason"):
        assert response.json()[field] == payment[field]

    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json()["status"] == "succeeded"
    for field in ("id", "booking_id", "amount", "currency", "failure_reason"):
        assert saved_payment.json()[field] == payment[field]

    confirmed = get_booking(base_url, user_access_token, booking["id"])
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "confirmed"
    for field in (
        "id", "user_id", "room_id", "check_in", "check_out", "guests",
        "price_per_night", "total_price", "currency",
    ):
        assert confirmed.json()[field] == booking[field]
