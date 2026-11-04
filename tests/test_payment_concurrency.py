from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from jsonschema import FormatChecker, validate

from api.bookings import cancel_booking, create_booking, get_booking
from api.payments import create_payment, get_payment, simulate_payment_success
from api.rooms import get_room_availability
from db import get_booking_payment_history, get_booking_payment_states
from schemas.payment_response import PAYMENT_SCHEMA
from tests.assertions import assert_api_error


@pytest.mark.db
def test_only_one_concurrent_payment_is_created(
    base_url, database_url, available_room, stay_dates, registered_user, user_access_token,
):
    payload = {"room_id": available_room["room"]["id"], **stay_dates}
    booked = create_booking(base_url, user_access_token, payload, uuid4().hex)
    assert booked.status_code == 201, booked.text
    booking = booked.json()
    assert booking["status"] == "pending_payment"
    assert booking["user_id"] == registered_user["user"]["id"]
    for field, value in payload.items():
        assert booking[field] == value
    assert get_booking_payment_states(database_url, booking["id"], booking["user_id"]) == []
    barrier = Barrier(2, timeout=10)

    def pay():
        barrier.wait()
        return create_payment(base_url, user_access_token, booking["id"])

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(pay) for _ in range(2)]
        responses = [future.result(timeout=30) for future in futures]

    diagnostics = [(response.status_code, response.text) for response in responses]
    assert sorted(response.status_code for response in responses) == [201, 409], diagnostics
    created = next(response for response in responses if response.status_code == 201)
    rejected = next(response for response in responses if response.status_code == 409)
    assert_api_error(rejected, status=409, code="PAYMENT_ALREADY_PENDING")
    assert created.headers.get("X-Request-ID")
    payment = created.json()
    validate(payment, PAYMENT_SCHEMA, format_checker=FormatChecker())
    assert payment["booking_id"] == booking["id"]
    assert payment["status"] == "pending"
    assert payment["failure_reason"] is None
    assert payment["amount"] == booking["total_price"]
    assert payment["currency"] == booking["currency"]
    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == payment
    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    assert saved_booking.json() == booking

    # The API has no payment list: count all rows, not only the known successful ID.
    assert get_booking_payment_states(database_url, booking["id"], booking["user_id"]) == [
        {"id": payment["id"], "status": "pending"},
    ]


@pytest.mark.db
def test_concurrent_payment_success_is_applied_only_once(
    base_url, database_url, pending_payment, user_access_token,
):
    booking = pending_payment["booking"]
    payment = pending_payment["payment"]
    actor_id = booking["user_id"]
    initial_history = {
        "booking": [{"from_status": None, "to_status": "pending_payment", "actor_id": actor_id}],
        "payment": [{"from_status": None, "to_status": "pending", "actor_id": actor_id}],
    }
    assert get_booking_payment_history(database_url, booking["id"], actor_id, payment["id"]) == initial_history
    barrier = Barrier(2, timeout=10)

    def succeed():
        barrier.wait()
        return simulate_payment_success(base_url, user_access_token, payment["id"])

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(succeed) for _ in range(2)]
        responses = [future.result(timeout=30) for future in futures]

    diagnostics = [(response.status_code, response.text) for response in responses]
    assert sorted(response.status_code for response in responses) == [200, 409], diagnostics
    succeeded = next(response for response in responses if response.status_code == 200)
    rejected = next(response for response in responses if response.status_code == 409)
    assert_api_error(rejected, status=409, code="BOOKING_NOT_PAYABLE")
    assert succeeded.headers.get("X-Request-ID")
    paid = succeeded.json()
    validate(paid, PAYMENT_SCHEMA, format_checker=FormatChecker())
    assert paid["status"] == "succeeded"
    for field in ("id", "booking_id", "amount", "currency", "failure_reason", "created_at"):
        assert paid[field] == payment[field]
    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == paid
    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    confirmed = saved_booking.json()
    assert confirmed["status"] == "confirmed"
    for field, value in booking.items():
        if field not in ("status", "updated_at"):
            assert confirmed[field] == value

    assert get_booking_payment_states(database_url, booking["id"], actor_id) == [
        {"id": payment["id"], "status": "succeeded"},
    ]
    # Check full histories: no duplicate success/confirmation or extra intermediate transitions.
    assert get_booking_payment_history(database_url, booking["id"], actor_id, payment["id"]) == {
        "booking": [*initial_history["booking"],
                    {"from_status": "pending_payment", "to_status": "confirmed", "actor_id": actor_id}],
        "payment": [*initial_history["payment"],
                    {"from_status": "pending", "to_status": "succeeded", "actor_id": actor_id}],
    }


@pytest.mark.db
def test_concurrent_payment_and_cancellation_have_consistent_result(
    base_url, database_url, pending_payment, user_access_token, stay_dates,
    record_testsuite_property,
):
    booking = pending_payment["booking"]
    payment = pending_payment["payment"]
    actor_id = booking["user_id"]
    initial_history = {
        "booking": [{"from_status": None, "to_status": "pending_payment", "actor_id": actor_id}],
        "payment": [{"from_status": None, "to_status": "pending", "actor_id": actor_id}],
    }
    assert get_booking_payment_history(database_url, booking["id"], actor_id, payment["id"]) == initial_history
    barrier = Barrier(2, timeout=10)

    def pay():
        barrier.wait()
        return simulate_payment_success(base_url, user_access_token, payment["id"])

    def cancel():
        barrier.wait()
        return cancel_booking(base_url, user_access_token, booking["id"])

    with ThreadPoolExecutor(max_workers=2) as executor:
        payment_future = executor.submit(pay)
        cancellation_future = executor.submit(cancel)
        payment_response = payment_future.result(timeout=30)
        cancellation_response = cancellation_future.result(timeout=30)

    assert cancellation_response.status_code == 200, cancellation_response.text
    assert cancellation_response.headers.get("X-Request-ID")
    assert payment_response.status_code in (200, 409), payment_response.text
    if payment_response.status_code == 200:
        outcome = "payment_first_refunded"
        final_payment_status = "refunded"
        paid = payment_response.json()
        validate(paid, PAYMENT_SCHEMA, format_checker=FormatChecker())
        assert paid["status"] == "succeeded"
        for field in ("id", "booking_id", "amount", "currency", "failure_reason", "created_at"):
            assert paid[field] == payment[field]
        assert payment_response.headers.get("X-Request-ID")
        booking_transitions = [
            {"from_status": "pending_payment", "to_status": "confirmed", "actor_id": actor_id},
            {"from_status": "confirmed", "to_status": "cancelled", "actor_id": actor_id},
        ]
        payment_transitions = [
            {"from_status": "pending", "to_status": "succeeded", "actor_id": actor_id},
            {"from_status": "succeeded", "to_status": "refunded", "actor_id": actor_id},
        ]
    else:
        outcome = "cancellation_first_payment_rejected"
        final_payment_status = "cancelled"
        assert_api_error(payment_response, status=409, code="BOOKING_NOT_PAYABLE")
        booking_transitions = [
            {"from_status": "pending_payment", "to_status": "cancelled", "actor_id": actor_id},
        ]
        payment_transitions = [
            {"from_status": "pending", "to_status": "cancelled", "actor_id": actor_id},
        ]
    record_testsuite_property("payment_cancellation_outcome", outcome)

    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    cancelled = saved_booking.json()
    assert cancelled["status"] == "cancelled"
    assert cancelled == cancellation_response.json()
    for field, value in booking.items():
        if field not in ("status", "updated_at"):
            assert cancelled[field] == value
    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    final_payment = saved_payment.json()
    validate(final_payment, PAYMENT_SCHEMA, format_checker=FormatChecker())
    assert final_payment["status"] == final_payment_status
    for field, value in payment.items():
        if field not in ("status", "updated_at"):
            assert final_payment[field] == value

    availability = get_room_availability(base_url, booking["room_id"], stay_dates)
    assert availability.status_code == 200, availability.text
    assert availability.json()["available"] is True
    assert availability.json()["reason"] is None
    assert get_booking_payment_states(database_url, booking["id"], actor_id) == [
        {"id": payment["id"], "status": final_payment_status},
    ]
    assert get_booking_payment_history(database_url, booking["id"], actor_id, payment["id"]) == {
        "booking": [*initial_history["booking"], *booking_transitions],
        "payment": [*initial_history["payment"], *payment_transitions],
    }
