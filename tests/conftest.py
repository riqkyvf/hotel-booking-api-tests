import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from dotenv import load_dotenv

from api.auth import login, register
from api.bookings import create_booking, get_booking
from api.hotels import create_hotel
from api.payments import create_payment, get_payment, simulate_payment_success
from api.rooms import create_room
from api.users import update_user_as_admin
from data.booking import (
    BLOCKING_BOOKING_STATUSES,
    BOOKING_CHECK_IN_OFFSET_DAYS, BOOKING_GUESTS, BOOKING_NIGHTS, BOOKING_ROOM_DATA,
)
from data.hotels import HOTEL_TEMPLATE


load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


@pytest.fixture(scope="session")
def base_url():
    url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1").strip().rstrip("/")
    if not url:
        pytest.fail("API_BASE_URL must not be empty", pytrace=False)
    return url


@pytest.fixture
def user_data():
    return {
        "email": f"user_{uuid4().hex}@example.com",
        "password": "password12345",
        "name": "Evgeniy",
    }


@pytest.fixture
def login_data(user_data):
    return {
        "email": user_data["email"],
        "password": user_data["password"],
    }


@pytest.fixture
def email_254():
    local_part = uuid4().hex * 2
    domain = ".".join(["a" * 63, "b" * 63, "c" * 61])
    return f"{local_part}@{domain}"


@pytest.fixture
def registered_user(base_url, user_data):
    """Return registration payload (including password) and the server user snapshot."""
    response = register(base_url, user_data)

    assert response.status_code == 201, response.text

    return {"payload": user_data.copy(), "user": response.json()}


@pytest.fixture
def registered_login_data(registered_user):
    """Return email/password credentials for the newly registered user."""
    return {
        "email": registered_user["payload"]["email"],
        "password": registered_user["payload"]["password"],
    }


@pytest.fixture
def user_access_token(base_url, registered_login_data):
    response = login(base_url, registered_login_data)

    assert response.status_code == 200, response.text

    return response.json()["access_token"]


@pytest.fixture
def admin_access_token(base_url):
    email = os.getenv("API_ADMIN_EMAIL")
    password = os.getenv("API_ADMIN_PASSWORD")
    if not email or not password:
        pytest.fail(
            "Set API_ADMIN_EMAIL and API_ADMIN_PASSWORD in the environment or .env "
            "for administrative scenarios",
            pytrace=False,
        )

    response = login(
        base_url,
        {
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200, response.text

    return response.json()["access_token"]


@pytest.fixture
def disabled_user_credentials(base_url, registered_user, admin_access_token):
    """Return registration credentials after disabling this test's user."""
    user_id = registered_user["user"]["id"]

    update_response = update_user_as_admin(
        base_url,
        admin_access_token,
        user_id,
        {"is_active": False},
    )

    assert update_response.status_code == 200, update_response.text
    updated_user = update_response.json()
    assert updated_user["id"] == user_id
    assert updated_user["is_active"] is False

    return registered_user["payload"].copy()


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

    return {"hotel": hotel, "room": room}


@pytest.fixture
def stay_dates():
    check_in = datetime.now(timezone.utc).date() + timedelta(days=BOOKING_CHECK_IN_OFFSET_DAYS)
    check_out = check_in + timedelta(days=BOOKING_NIGHTS)
    stay = {
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "guests": BOOKING_GUESTS,
    }
    return stay


@pytest.fixture
def second_user(base_url, user_data):
    """Register and log in another user; return {id, access_token}."""
    payload = {**user_data, "email": f"second_{uuid4().hex}@example.com"}
    registered = register(base_url, payload)
    assert registered.status_code == 201, registered.text
    user = registered.json()

    logged_in = login(base_url, {"email": payload["email"], "password": payload["password"]})
    assert logged_in.status_code == 200, logged_in.text
    return {"id": user["id"], "access_token": logged_in.json()["access_token"]}


@pytest.fixture
def pending_payment(base_url, available_room, stay_dates, registered_user, user_access_token):
    """Return {booking, payment} snapshots in pending_payment/pending states."""
    payload = {"room_id": available_room["room"]["id"], **stay_dates}
    booked = create_booking(base_url, user_access_token, payload, uuid4().hex)
    assert booked.status_code == 201, booked.text
    booking = booked.json()
    assert booking["status"] == "pending_payment"
    assert booking["user_id"] == registered_user["user"]["id"]
    for field, value in payload.items():
        assert booking[field] == value

    created = create_payment(base_url, user_access_token, booking["id"])
    assert created.status_code == 201, created.text
    payment = created.json()
    assert payment["booking_id"] == booking["id"]
    assert payment["status"] == "pending"
    assert payment["failure_reason"] is None
    assert payment["amount"] == booking["total_price"]
    assert payment["currency"] == booking["currency"]
    return {"booking": booking, "payment": payment}


@pytest.fixture(params=BLOCKING_BOOKING_STATUSES)
def booking_with_payment(base_url, pending_payment, user_access_token, request):
    """Return current {booking, payment}; run consumers for pending_payment and confirmed bookings."""
    booking = pending_payment["booking"]
    payment = pending_payment["payment"]

    if request.param == "confirmed":
        succeeded = simulate_payment_success(base_url, user_access_token, payment["id"])
        assert succeeded.status_code == 200, succeeded.text
        assert succeeded.json()["status"] == "succeeded"

    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    booking_body = saved_booking.json()
    assert booking_body["id"] == booking["id"]
    assert booking_body["user_id"] == booking["user_id"]
    assert booking_body["status"] == request.param

    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    payment_body = saved_payment.json()
    assert payment_body["id"] == payment["id"]
    assert payment_body["booking_id"] == booking["id"]
    expected_status = "succeeded" if request.param == "confirmed" else "pending"
    assert payment_body["status"] == expected_status
    return {"booking": booking_body, "payment": payment_body}


@pytest.fixture
def database_url():
    value = os.getenv("TEST_DATABASE_URL")
    if not value or not value.strip():
        pytest.fail("Set TEST_DATABASE_URL in the environment or .env for SQL preparation", pytrace=False)
    return value
