import pytest

from api.bookings import get_booking
from api.payments import get_payment, simulate_payment_failure
from tests.assertions import assert_api_error


@pytest.mark.parametrize("reason", ["x", "x" * 250], ids=["min_length", "max_length"])
def test_payment_failure_accepts_reason_boundaries(base_url, pending_payment, user_access_token, reason):
    payment = pending_payment["payment"]
    response = simulate_payment_failure(base_url, user_access_token, payment["id"], {"reason": reason})
    assert response.status_code == 200, response.text
    failed = response.json()
    assert failed["failure_reason"] == reason
    assert failed["status"] == "failed"
    for field in ("id", "booking_id", "amount", "currency"):
        assert failed[field] == payment[field]
    saved = get_payment(base_url, user_access_token, payment["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == failed
    booking = get_booking(base_url, user_access_token, pending_payment["booking"]["id"])
    assert booking.status_code == 200, booking.text
    assert booking.json() == pending_payment["booking"]


@pytest.mark.parametrize("payload", [
    {"reason": ""}, {"reason": "x" * 251}, {"reason": None}, {"reason": 123},
    {"reason": True}, {"reason": []}, {"reason": {}},
    {"unexpected": "value"}, {"status": "succeeded"}, {"amount": "0.01"},
])
def test_payment_failure_rejects_invalid_fields(base_url, pending_payment, user_access_token, payload):
    payment = pending_payment["payment"]
    response = simulate_payment_failure(base_url, user_access_token, payment["id"], payload)
    body = assert_api_error(response, status=422, code="VALIDATION_ERROR")
    field = next(iter(payload))
    assert any(item["field"] == f"body.{field}" for item in body["error"]["details"])
    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == payment
    saved_booking = get_booking(base_url, user_access_token, pending_payment["booking"]["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    assert saved_booking.json() == pending_payment["booking"]


@pytest.mark.parametrize("raw_body", ['{"reason":', "[]"], ids=["malformed_json", "array"])
def test_payment_failure_rejects_invalid_json_body(base_url, pending_payment, user_access_token, raw_body):
    payment = pending_payment["payment"]
    response = simulate_payment_failure(base_url, user_access_token, payment["id"], raw_body=raw_body)
    assert_api_error(response, status=422, code="VALIDATION_ERROR")
    saved_payment = get_payment(base_url, user_access_token, payment["id"])
    assert saved_payment.status_code == 200, saved_payment.text
    assert saved_payment.json() == payment
    saved_booking = get_booking(base_url, user_access_token, pending_payment["booking"]["id"])
    assert saved_booking.status_code == 200, saved_booking.text
    assert saved_booking.json() == pending_payment["booking"]
