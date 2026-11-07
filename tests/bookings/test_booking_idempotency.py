from datetime import datetime
from urllib.parse import urlparse
from uuid import uuid4

import pytest

from api.bookings import cancel_booking, create_booking, get_booking, list_bookings
from api.payments import create_payment, get_payment, simulate_payment_success
from api.rooms import get_room_availability
from db import move_booking_expiry_to_past
from tests.assertions import assert_api_error


@pytest.fixture
def idempotent_booking(base_url, available_room, stay_dates, user_access_token):
    payload = {"room_id": available_room["room"]["id"], **stay_dates}
    key = uuid4().hex
    response = create_booking(base_url, user_access_token, payload, key)
    assert response.status_code == 201, response.text
    booking = response.json()
    assert booking["status"] == "pending_payment"
    for field, value in payload.items():
        assert booking[field] == value
    assert response.headers.get("Idempotency-Replayed", "").lower() == "false"
    location = response.headers.get("Location")
    assert location
    assert urlparse(location).path == f"{urlparse(base_url).path}/bookings/{booking['id']}"
    return {"booking": booking, "payload": payload, "key": key, "location": location}


def test_same_key_and_body_replay_original_booking(base_url, idempotent_booking, user_access_token):
    booking = idempotent_booking["booking"]
    # Reordering JSON fields must not change the validated request.
    reordered = dict(reversed(list(idempotent_booking["payload"].items())))
    response = create_booking(base_url, user_access_token, reordered, idempotent_booking["key"])
    assert response.status_code == 201, response.text
    assert response.json() == booking
    assert response.headers.get("Idempotency-Replayed", "").lower() == "true"
    assert response.headers.get("Location") == idempotent_booking["location"]

    saved = get_booking(base_url, user_access_token, booking["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == booking
    bookings = list_bookings(base_url, user_access_token)
    assert bookings.status_code == 200, bookings.text
    page = bookings.json()
    assert page["total"] == 1
    assert [item["id"] for item in page["items"]] == [booking["id"]]


def test_same_key_with_different_body_is_rejected(base_url, idempotent_booking, user_access_token):
    booking = idempotent_booking["booking"]
    changed = {**idempotent_booking["payload"], "guests": 1}
    assert changed != idempotent_booking["payload"]
    response = create_booking(base_url, user_access_token, changed, idempotent_booking["key"])
    assert_api_error(response, status=409, code="IDEMPOTENCY_KEY_REUSED")

    saved = get_booking(base_url, user_access_token, booking["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == booking
    bookings = list_bookings(base_url, user_access_token)
    assert bookings.status_code == 200, bookings.text
    page = bookings.json()
    assert page["total"] == 1
    assert [item["id"] for item in page["items"]] == [booking["id"]]


def test_replay_after_cancellation_does_not_create_new_booking(
    base_url, stay_dates, idempotent_booking, user_access_token,
):
    booking = idempotent_booking["booking"]
    cancelled_response = cancel_booking(base_url, user_access_token, booking["id"])
    assert cancelled_response.status_code == 200, cancelled_response.text
    cancelled = cancelled_response.json()
    assert cancelled["id"] == booking["id"]
    assert cancelled["status"] == "cancelled"

    response = create_booking(
        base_url, user_access_token, idempotent_booking["payload"], idempotent_booking["key"],
    )
    assert response.status_code == 201, response.text
    assert response.json() == booking
    assert response.headers.get("Idempotency-Replayed", "").lower() == "true"
    assert response.headers.get("Location") == idempotent_booking["location"]

    saved = get_booking(base_url, user_access_token, booking["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == cancelled
    bookings = list_bookings(base_url, user_access_token)
    assert bookings.status_code == 200, bookings.text
    page = bookings.json()
    assert page["total"] == 1
    assert [item["id"] for item in page["items"]] == [booking["id"]]

    availability = get_room_availability(base_url, booking["room_id"], stay_dates)
    assert availability.status_code == 200, availability.text
    body = availability.json()
    assert body["room_id"] == booking["room_id"]
    assert body["available"] is True
    assert body["reason"] is None


def test_replay_after_payment_preserves_confirmed_booking(
    base_url, idempotent_booking, user_access_token,
):
    booking = idempotent_booking["booking"]
    created = create_payment(base_url, user_access_token, booking["id"])
    assert created.status_code == 201, created.text
    payment = created.json()
    assert payment["status"] == "pending"
    succeeded = simulate_payment_success(base_url, user_access_token, payment["id"])
    assert succeeded.status_code == 200, succeeded.text
    paid = succeeded.json()
    assert paid["id"] == payment["id"]
    assert paid["status"] == "succeeded"
    confirmed_response = get_booking(base_url, user_access_token, booking["id"])
    assert confirmed_response.status_code == 200, confirmed_response.text
    confirmed = confirmed_response.json()
    assert confirmed["status"] == "confirmed"
    assert confirmed["expires_at"] == booking["expires_at"]

    response = create_booking(
        base_url, user_access_token, idempotent_booking["payload"], idempotent_booking["key"],
    )
    assert response.status_code == 201, response.text
    assert response.json() == booking
    assert response.headers.get("Idempotency-Replayed", "").lower() == "true"
    assert response.headers.get("Location") == idempotent_booking["location"]

    saved = get_booking(base_url, user_access_token, booking["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == confirmed
    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == paid
    bookings = list_bookings(base_url, user_access_token)
    assert bookings.status_code == 200, bookings.text
    page = bookings.json()
    assert page["total"] == 1
    assert [item["id"] for item in page["items"]] == [booking["id"]]


@pytest.mark.db
def test_replay_after_expiration_preserves_expired_booking(
    base_url, database_url, idempotent_booking, user_access_token,
):
    original = idempotent_booking["booking"]
    booking_id = original["id"]
    expires_at = move_booking_expiry_to_past(database_url, booking_id, original["user_id"])
    before_replay = get_booking(base_url, user_access_token, booking_id)
    assert before_replay.status_code == 200, before_replay.text
    expired = before_replay.json()
    assert expired["status"] == "expired"
    assert datetime.fromisoformat(expired["expires_at"]) == expires_at

    replay = create_booking(
        base_url, user_access_token, idempotent_booking["payload"], idempotent_booking["key"],
    )
    assert replay.status_code == 201, replay.text
    assert replay.json() == original
    assert replay.headers.get("Idempotency-Replayed", "").lower() == "true"
    assert replay.headers.get("Location") == idempotent_booking["location"]

    saved = get_booking(base_url, user_access_token, booking_id)
    assert saved.status_code == 200, saved.text
    assert saved.json() == expired
    bookings = list_bookings(base_url, user_access_token)
    assert bookings.status_code == 200, bookings.text
    assert bookings.json()["total"] == 1
    assert [item["id"] for item in bookings.json()["items"]] == [booking_id]
