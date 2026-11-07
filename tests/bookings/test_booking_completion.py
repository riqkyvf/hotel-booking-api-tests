from datetime import date
from uuid import uuid4

import pytest
from jsonschema import FormatChecker, validate

from api.bookings import cancel_booking, create_booking, get_booking, list_bookings
from api.payments import create_payment, get_payment, simulate_payment_failure, simulate_payment_success
from db import (get_booking_payment_history, get_booking_payment_states,
                move_confirmed_booking_checkout_to_today)
from schemas.booking_response import BOOKING_SCHEMA
from schemas.payment_response import PAYMENT_SCHEMA
from tests.assertions import assert_api_error


pytestmark = pytest.mark.db


@pytest.fixture
def checkout_booking(base_url, database_url, available_room, stay_dates, user_access_token):
    payload = {"room_id": available_room["room"]["id"], **stay_dates}
    key = uuid4().hex
    created = create_booking(base_url, user_access_token, payload, key)
    assert created.status_code == 201, created.text
    original = created.json()
    payment_response = create_payment(base_url, user_access_token, original["id"])
    assert payment_response.status_code == 201, payment_response.text
    succeeded = simulate_payment_success(base_url, user_access_token, payment_response.json()["id"])
    assert succeeded.status_code == 200, succeeded.text
    assert succeeded.json()["status"] == "succeeded"
    confirmed = get_booking(base_url, user_access_token, original["id"])
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "confirmed"
    dates = move_confirmed_booking_checkout_to_today(database_url, original["id"], original["user_id"])
    assert (date.fromisoformat(dates["check_out"]) - date.fromisoformat(dates["check_in"])).days == (
        date.fromisoformat(original["check_out"]) - date.fromisoformat(original["check_in"])
    ).days
    return {"original": original, "expected": {**confirmed.json(), **dates, "status": "completed"},
            "payment": succeeded.json(), "payload": payload, "key": key,
            "location": created.headers["Location"]}


def assert_completed_state(base_url, database_url, token, context):
    expected = context["expected"]
    saved = get_booking(base_url, token, expected["id"])
    assert saved.status_code == 200, saved.text
    booking = saved.json()
    validate(booking, BOOKING_SCHEMA, format_checker=FormatChecker())
    for field, value in expected.items():
        if field != "updated_at":
            assert booking[field] == value, field
    payment = context["payment"]
    saved_payment = get_payment(base_url, token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    validate(saved_payment.json(), PAYMENT_SCHEMA, format_checker=FormatChecker())
    assert saved_payment.json() == payment
    actor = booking["user_id"]
    assert get_booking_payment_states(database_url, booking["id"], actor) == [
        {"id": payment["id"], "status": "succeeded"},
    ]
    assert get_booking_payment_history(database_url, booking["id"], actor, payment["id"]) == {
        "booking": [
            {"from_status": None, "to_status": "pending_payment", "actor_id": actor},
            {"from_status": "pending_payment", "to_status": "confirmed", "actor_id": actor},
            {"from_status": "confirmed", "to_status": "completed", "actor_id": None},
        ],
        "payment": [
            {"from_status": None, "to_status": "pending", "actor_id": actor},
            {"from_status": "pending", "to_status": "succeeded", "actor_id": actor},
        ],
    }
    return booking


@pytest.mark.parametrize("reader", ["booking", "payment", "list"])
def test_confirmed_stay_completes_on_checkout_day(
    base_url, database_url, checkout_booking, user_access_token, reader,
):
    context = checkout_booking
    if reader == "booking":
        response = get_booking(base_url, user_access_token, context["original"]["id"])
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "completed"
    elif reader == "payment":
        response = get_payment(base_url, user_access_token, context["payment"]["id"])
        assert response.status_code == 200, response.text
        assert response.json() == context["payment"]
    else:
        response = list_bookings(base_url, user_access_token, {"status": "completed"})
        assert response.status_code == 200, response.text
        assert response.json()["total"] == 1
        assert [item["id"] for item in response.json()["items"]] == [context["original"]["id"]]
    completed = assert_completed_state(base_url, database_url, user_access_token, context)
    # Repeated reads must preserve the terminal state and produce no duplicate history.
    assert assert_completed_state(base_url, database_url, user_access_token, context) == completed


@pytest.mark.parametrize("operation", ["cancel", "create_payment", "success", "failure"])
def test_completed_booking_rejects_changes(
    base_url, database_url, checkout_booking, user_access_token, operation,
):
    context = checkout_booking
    completed = assert_completed_state(base_url, database_url, user_access_token, context)
    booking_id, payment_id = completed["id"], context["payment"]["id"]
    if operation == "cancel":
        response = cancel_booking(base_url, user_access_token, booking_id)
    elif operation == "create_payment":
        response = create_payment(base_url, user_access_token, booking_id)
    elif operation == "success":
        response = simulate_payment_success(base_url, user_access_token, payment_id)
    else:
        response = simulate_payment_failure(base_url, user_access_token, payment_id, {"reason": "Must not change"})
    assert_api_error(response, status=409, code=(
        "BOOKING_STATE_CONFLICT" if operation == "cancel" else "BOOKING_NOT_PAYABLE"
    ))
    assert assert_completed_state(base_url, database_url, user_access_token, context) == completed


def test_idempotency_replay_preserves_completed_booking(
    base_url, database_url, checkout_booking, user_access_token,
):
    context = checkout_booking
    completed = assert_completed_state(base_url, database_url, user_access_token, context)
    replay = create_booking(base_url, user_access_token, context["payload"], context["key"])
    assert replay.status_code == 201, replay.text
    assert replay.json() == context["original"]
    assert replay.headers.get("Idempotency-Replayed", "").lower() == "true"
    assert replay.headers.get("Location") == context["location"]
    assert assert_completed_state(base_url, database_url, user_access_token, context) == completed
    listed = list_bookings(base_url, user_access_token)
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] == 1
    assert listed.json()["items"] == [completed]
