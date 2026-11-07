from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from jsonschema import FormatChecker, validate

from api.bookings import cancel_booking, get_booking
from api.payments import get_payment, simulate_payment_failure, simulate_payment_success
from db import move_booking_expiry_to_past
from schemas.booking_response import BOOKING_SCHEMA
from schemas.payment_response import PAYMENT_SCHEMA
from tests.assertions import assert_api_error


@pytest.fixture
def readable_resources(base_url, pending_payment, user_access_token, request):
    """Prepare and reread actual API snapshots; only expires_at uses existing SQL preparation."""
    booking = pending_payment["booking"]
    payment = pending_payment["payment"]
    state = request.param
    if state in ("confirmed", "refunded"):
        paid = simulate_payment_success(base_url, user_access_token, payment["id"])
        assert paid.status_code == 200, paid.text
        assert paid.json()["status"] == "succeeded"
    if state in ("cancelled", "refunded"):
        cancelled = cancel_booking(base_url, user_access_token, booking["id"])
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["status"] == "cancelled"
    elif state == "failed":
        failed = simulate_payment_failure(base_url, user_access_token, payment["id"], {"reason": "Read contract test"})
        assert failed.status_code == 200, failed.text
        assert failed.json()["status"] == "failed"
    elif state == "expired":
        move_booking_expiry_to_past(request.getfixturevalue("database_url"), booking["id"], booking["user_id"])
    saved_booking = get_booking(base_url, user_access_token, booking["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    expected_booking, expected_payment = {
        "pending": ("pending_payment", "pending"), "confirmed": ("confirmed", "succeeded"),
        "cancelled": ("cancelled", "cancelled"), "refunded": ("cancelled", "refunded"),
        "failed": ("pending_payment", "failed"), "expired": ("expired", "cancelled"),
    }[state]
    assert saved_booking.json()["status"] == expected_booking
    assert saved_payment.json()["status"] == expected_payment
    return {"booking": saved_booking.json(), "payment": saved_payment.json()}


@pytest.mark.parametrize("readable_resources", [
    "pending", "confirmed", "failed", "cancelled", "refunded", pytest.param("expired", marks=pytest.mark.db),
], indirect=True)
@pytest.mark.parametrize("reader", ["owner", "admin"])
@pytest.mark.parametrize("resource", ["booking", "payment"])
def test_booking_and_payment_read_response_contract(
    base_url, user_access_token, admin_access_token, readable_resources, reader, resource,
):
    booking = readable_resources["booking"]
    payment = readable_resources["payment"]
    token = user_access_token if reader == "owner" else admin_access_token
    expected = readable_resources[resource]
    response = (get_booking(base_url, token, booking["id"]) if resource == "booking"
                else get_payment(base_url, token, payment["id"]))
    assert response.status_code == 200, response.text
    body = response.json()
    validate(body, BOOKING_SCHEMA if resource == "booking" else PAYMENT_SCHEMA, format_checker=FormatChecker())
    assert body == expected
    assert response.headers.get("X-Request-ID")
    assert "password" not in body
    assert "password_hash" not in body
    assert "access_token" not in body
    for field in ("created_at", "updated_at"):
        assert datetime.fromisoformat(body[field]).utcoffset() == timedelta(0)
    assert datetime.fromisoformat(body["updated_at"]) >= datetime.fromisoformat(body["created_at"])
    if resource == "booking":
        nights = (date.fromisoformat(body["check_out"]) - date.fromisoformat(body["check_in"])).days
        assert 1 <= nights <= 14
        assert Decimal(body["price_per_night"]) > 0
        assert Decimal(body["total_price"]) == Decimal(body["price_per_night"]) * nights
        assert datetime.fromisoformat(body["expires_at"]).utcoffset() == timedelta(0)
    else:
        assert body["booking_id"] == booking["id"]
        assert Decimal(body["amount"]) > 0
        assert body["amount"] == booking["total_price"]
        assert body["currency"] == booking["currency"]


@pytest.mark.parametrize("resource", ["booking", "payment"])
@pytest.mark.parametrize("reader", ["owner", "admin"])
def test_read_unknown_booking_or_payment(base_url, user_access_token, admin_access_token, resource, reader):
    token = user_access_token if reader == "owner" else admin_access_token
    identifier = str(uuid4())
    response = (get_booking(base_url, token, identifier) if resource == "booking"
                else get_payment(base_url, token, identifier))
    assert_api_error(response, status=404, code="NOT_FOUND")


@pytest.mark.parametrize("resource", ["booking", "payment"])
def test_read_booking_or_payment_rejects_invalid_uuid(base_url, user_access_token, resource):
    read = get_booking if resource == "booking" else get_payment
    response = read(base_url, user_access_token, "not-a-uuid")
    body = assert_api_error(response, status=422, code="VALIDATION_ERROR")
    assert any(item["field"] == f"path.{resource}_id" for item in body["error"]["details"])
