from datetime import date, timedelta
from uuid import uuid4

import pytest

from api.bookings import create_booking, get_booking, list_bookings
from api.rooms import get_room_availability
from tests.assertions import assert_api_error


@pytest.fixture
def booking_payload(available_room, stay_dates):
    return {"room_id": available_room["room"]["id"], **stay_dates}


@pytest.mark.parametrize("key", [None, "", "x" * 129, "has space", "a/b", "a!", "a@b"],
                         ids=["missing", "empty", "too_long", "space", "slash", "punctuation", "at"])
def test_booking_rejects_invalid_idempotency_key(base_url, user_access_token, booking_payload, key):
    response = create_booking(base_url, user_access_token, booking_payload, key)
    assert_api_error(response, status=422, code="VALIDATION_ERROR")
    bookings = list_bookings(base_url, user_access_token)
    assert bookings.status_code == 200, bookings.text
    assert bookings.json()["total"] == 0
    assert bookings.json()["items"] == []
    availability = get_room_availability(base_url, booking_payload["room_id"], {
        field: booking_payload[field] for field in ("check_in", "check_out", "guests")
    })
    assert availability.status_code == 200, availability.text
    assert availability.json()["available"] is True


@pytest.mark.parametrize("key", ["a", "x" * 128, "Az09._:-"], ids=["min", "max", "allowed_characters"])
def test_booking_accepts_valid_idempotency_key(base_url, user_access_token, booking_payload, key):
    response = create_booking(base_url, user_access_token, booking_payload, key)
    assert response.status_code == 201, response.text
    booking = response.json()
    assert response.headers.get("Idempotency-Replayed", "").lower() == "false"
    replay = create_booking(base_url, user_access_token, booking_payload, key)
    assert replay.status_code == 201, replay.text
    assert replay.json() == booking
    assert replay.headers.get("Idempotency-Replayed", "").lower() == "true"


@pytest.mark.parametrize("field", ["room_id", "check_in", "check_out", "guests"])
def test_booking_requires_fields_and_does_not_consume_key(base_url, user_access_token, booking_payload, field):
    invalid = booking_payload.copy()
    del invalid[field]
    key = uuid4().hex
    response = create_booking(base_url, user_access_token, invalid, key)
    body = assert_api_error(response, status=422, code="VALIDATION_ERROR")
    assert any(item["field"] == f"body.{field}" for item in body["error"]["details"])
    bookings = list_bookings(base_url, user_access_token)
    assert bookings.status_code == 200, bookings.text
    assert bookings.json()["total"] == 0
    corrected = create_booking(base_url, user_access_token, booking_payload, key)
    assert corrected.status_code == 201, corrected.text
    assert corrected.headers.get("Idempotency-Replayed", "").lower() == "false"


@pytest.mark.parametrize("field,value", [
    ("room_id", "not-a-uuid"), ("room_id", None),
    ("guests", 0), ("guests", 11), ("guests", True), ("guests", 1.5), ("guests", "2"), ("guests", None),
    ("check_in", "2030-13-01"), ("check_out", "2030-02-30"),
    ("check_in", "2030-01-01T00:00:00Z"), ("check_out", 1234567890),
    ("check_in", None), ("check_out", None),
    ("total_price", "0.01"), ("price_per_night", "0.01"),
    ("user_id", "someone_else"), ("status", "confirmed"), ("unexpected", "value"),
])
def test_booking_rejects_invalid_body_fields(base_url, user_access_token, booking_payload, field, value):
    response = create_booking(base_url, user_access_token, {**booking_payload, field: value}, uuid4().hex)
    body = assert_api_error(response, status=422, code="VALIDATION_ERROR")
    assert any(item["field"] == f"body.{field}" for item in body["error"]["details"])
    bookings = list_bookings(base_url, user_access_token)
    assert bookings.status_code == 200, bookings.text
    assert bookings.json()["total"] == 0
    assert bookings.json()["items"] == []


@pytest.mark.parametrize("raw_body", ['{"room_id":', "[]"], ids=["malformed_json", "array"])
def test_booking_rejects_invalid_json_body(base_url, user_access_token, booking_payload, raw_body):
    key = uuid4().hex
    response = create_booking(base_url, user_access_token, idempotency_key=key, raw_body=raw_body)
    assert_api_error(response, status=422, code="VALIDATION_ERROR")
    bookings = list_bookings(base_url, user_access_token)
    assert bookings.status_code == 200, bookings.text
    assert bookings.json()["total"] == 0
    corrected = create_booking(base_url, user_access_token, booking_payload, key)
    assert corrected.status_code == 201, corrected.text
    assert corrected.headers.get("Idempotency-Replayed", "").lower() == "false"


def test_idempotency_key_is_scoped_to_user(base_url, user_access_token, second_user, booking_payload):
    # Same room, disjoint dates: a conflict must not be caused by room occupancy.
    key = uuid4().hex
    first = create_booking(base_url, user_access_token, booking_payload, key)
    assert first.status_code == 201, first.text
    nights = (date.fromisoformat(booking_payload["check_out"]) - date.fromisoformat(booking_payload["check_in"])).days
    check_in = date.fromisoformat(booking_payload["check_out"])
    other_payload = {**booking_payload, "check_in": check_in.isoformat(),
                     "check_out": (check_in + timedelta(days=nights)).isoformat()}
    second = create_booking(base_url, second_user["access_token"], other_payload, key)
    assert second.status_code == 201, second.text
    assert second.headers.get("Idempotency-Replayed", "").lower() == "false"
    assert second.json()["id"] != first.json()["id"]
    assert second.json()["user_id"] == second_user["id"]
    for token, payload, booking in ((user_access_token, booking_payload, first.json()),
                                    (second_user["access_token"], other_payload, second.json())):
        replay = create_booking(base_url, token, payload, key)
        assert replay.status_code == 201, replay.text
        assert replay.json() == booking
        assert replay.headers.get("Idempotency-Replayed", "").lower() == "true"
        saved = get_booking(base_url, token, booking["id"])
        assert saved.status_code == 200, saved.text
        assert saved.json() == booking
        listed = list_bookings(base_url, token)
        assert listed.status_code == 200, listed.text
        assert listed.json()["total"] == 1
        assert [item["id"] for item in listed.json()["items"]] == [booking["id"]]
