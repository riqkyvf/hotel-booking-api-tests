from uuid import uuid4

import pytest
from jsonschema import FormatChecker, validate

from api.hotels import archive_hotel, get_hotel
from api.rooms import (
    archive_room, create_room, get_room, get_room_availability, list_rooms,
    update_room, update_room_availability,
)
from data.booking import BOOKING_ROOM_DATA
from schemas.room_response import ROOM_SCHEMA
from tests.assertions import assert_api_error


@pytest.mark.parametrize("changes", [
    {"room_number": "x"}, {"room_number": "x" * 20},
    {"type": "single"}, {"type": "double"}, {"type": "twin"}, {"type": "family"}, {"type": "suite"},
    {"capacity": 1}, {"capacity": 10},
    {"price_per_night": "0.01"}, {"price_per_night": "9999999999.99"},
    {"room_number": "202", "type": "suite", "capacity": 4, "price_per_night": "3000.00"},
])
def test_admin_can_update_room(base_url, admin_access_token, available_room, changes):
    room = available_room["room"]
    payload = {**BOOKING_ROOM_DATA, **changes}
    response = update_room(base_url, admin_access_token, room["id"], payload)
    assert response.status_code == 200, response.text
    updated = response.json()
    validate(updated, ROOM_SCHEMA, format_checker=FormatChecker())
    for field, value in payload.items():
        assert updated[field] == value
    for field in ("id", "hotel_id", "created_at", "is_available", "is_archived"):
        assert updated[field] == room[field]
    assert response.headers.get("X-Request-ID")
    saved = get_room(base_url, room["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == updated
    hotel = get_hotel(base_url, room["hotel_id"])
    assert hotel.status_code == 200, hotel.text
    assert hotel.json() == available_room["hotel"]


@pytest.mark.parametrize("field", tuple(BOOKING_ROOM_DATA))
def test_room_put_requires_full_input(base_url, admin_access_token, available_room, field):
    room = available_room["room"]
    payload = BOOKING_ROOM_DATA.copy()
    del payload[field]
    response = update_room(base_url, admin_access_token, room["id"], payload)
    body = assert_api_error(response, status=422, code="VALIDATION_ERROR")
    assert any(item["field"] == f"body.{field}" for item in body["error"]["details"])
    saved = get_room(base_url, room["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == room


@pytest.mark.parametrize("field,value", [
    ("room_number", ""), ("room_number", "x" * 21), ("room_number", 123),
    ("type", "unknown"), ("capacity", 0), ("capacity", 11), ("capacity", True),
    ("capacity", "2"), ("capacity", 1.5),
    ("price_per_night", "0"), ("price_per_night", "-0.01"),
    ("price_per_night", "10000000000.00"), ("price_per_night", "1.001"), ("price_per_night", "text"),
    ("hotel_id", str(uuid4())), ("is_archived", True), ("is_available", False), ("unexpected", "x"),
] + [(field, None) for field in BOOKING_ROOM_DATA])
def test_room_put_rejects_invalid_fields_without_changes(base_url, admin_access_token, available_room, field, value):
    room = available_room["room"]
    response = update_room(base_url, admin_access_token, room["id"], {**BOOKING_ROOM_DATA, field: value})
    body = assert_api_error(response, status=422, code="VALIDATION_ERROR")
    assert any(item["field"] == f"body.{field}" for item in body["error"]["details"])
    saved = get_room(base_url, room["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == room


def test_room_update_rejects_duplicate_number_without_partial_changes(base_url, admin_access_token, available_room):
    room = available_room["room"]
    created = create_room(base_url, admin_access_token, room["hotel_id"], {**BOOKING_ROOM_DATA, "room_number": "202"})
    assert created.status_code == 201, created.text
    other = created.json()
    response = update_room(base_url, admin_access_token, room["id"],
                           {**BOOKING_ROOM_DATA, "room_number": "202", "price_per_night": "9999.99"})
    assert_api_error(response, status=409, code="ROOM_NUMBER_EXISTS")
    for expected in (room, other):
        saved = get_room(base_url, expected["id"])
        assert saved.status_code == 200, saved.text
        assert saved.json() == expected


def test_room_can_be_disabled_and_enabled(base_url, admin_access_token, available_room, stay_dates):
    room = available_room["room"]
    for enabled in (False, True):
        response = update_room_availability(base_url, admin_access_token, room["id"], {"is_available": enabled})
        assert response.status_code == 200, response.text
        updated = response.json()
        assert updated["is_available"] is enabled
        for field in (*BOOKING_ROOM_DATA, "id", "hotel_id", "created_at", "is_archived"):
            assert updated[field] == room[field]
        saved = get_room(base_url, room["id"])
        assert saved.status_code == 200, saved.text
        assert saved.json() == updated
        availability = get_room_availability(base_url, room["id"], stay_dates)
        assert availability.status_code == 200, availability.text
        assert availability.json()["available"] is enabled
        assert availability.json()["reason"] == (None if enabled else "ROOM_DISABLED")


@pytest.mark.parametrize("payload", [
    {}, {"is_available": None}, {"is_available": "false"}, {"is_available": "true"},
    {"is_available": 0}, {"is_available": 1}, {"is_available": []}, {"is_available": {}},
    {"is_available": False, "capacity": 1}, {"is_available": False, "unexpected": True},
])
def test_availability_patch_rejects_invalid_body_without_changes(base_url, admin_access_token, available_room, payload):
    room = available_room["room"]
    response = update_room_availability(base_url, admin_access_token, room["id"], payload)
    assert_api_error(response, status=422, code="VALIDATION_ERROR")
    saved = get_room(base_url, room["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == room


@pytest.mark.parametrize("operation", ["update", "availability"])
@pytest.mark.parametrize("raw_body", ['{"capacity":', "[]"], ids=["malformed_json", "array"])
def test_room_mutations_reject_invalid_json(base_url, admin_access_token, available_room, operation, raw_body):
    room = available_room["room"]
    if operation == "update":
        response = update_room(base_url, admin_access_token, room["id"], raw_body=raw_body)
    else:
        response = update_room_availability(base_url, admin_access_token, room["id"], raw_body=raw_body)
    assert_api_error(response, status=422, code="VALIDATION_ERROR")
    saved = get_room(base_url, room["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == room


@pytest.mark.parametrize("archived_parent", [False, True], ids=["archived_room", "archived_hotel"])
@pytest.mark.parametrize("operation", ["update", "availability"])
def test_archived_room_cannot_be_changed(base_url, admin_access_token, available_room, archived_parent, operation):
    room = available_room["room"]
    archived = (archive_hotel(base_url, admin_access_token, room["hotel_id"]) if archived_parent
                else archive_room(base_url, admin_access_token, room["id"]))
    assert archived.status_code == 204, archived.text
    before = get_room(base_url, room["id"], access_token=admin_access_token)
    assert before.status_code == 200, before.text
    assert before.json()["is_archived"] is True
    if operation == "update":
        response = update_room(base_url, admin_access_token, room["id"], {**BOOKING_ROOM_DATA, "capacity": 4})
    else:
        response = update_room_availability(base_url, admin_access_token, room["id"], {"is_available": True})
    assert_api_error(response, status=409, code="RESOURCE_ARCHIVED")
    saved = get_room(base_url, room["id"], access_token=admin_access_token)
    assert saved.status_code == 200, saved.text
    assert saved.json() == before.json()


def test_room_archiving_is_repeatable_and_does_not_archive_hotel(base_url, admin_access_token, available_room):
    room = available_room["room"]
    response = archive_room(base_url, admin_access_token, room["id"])
    assert response.status_code == 204, response.text
    assert response.content == b""
    hidden = get_room(base_url, room["id"])
    assert_api_error(hidden, status=404, code="NOT_FOUND")
    saved = get_room(base_url, room["id"], access_token=admin_access_token)
    assert saved.status_code == 200, saved.text
    archived = saved.json()
    assert archived["is_archived"] is True
    for field in (*BOOKING_ROOM_DATA, "id", "hotel_id", "created_at"):
        assert archived[field] == room[field]
    repeated = archive_room(base_url, admin_access_token, room["id"])
    assert repeated.status_code == 204, repeated.text
    assert repeated.content == b""
    saved_again = get_room(base_url, room["id"], access_token=admin_access_token)
    assert saved_again.status_code == 200, saved_again.text
    assert saved_again.json() == archived
    hotel = get_hotel(base_url, room["hotel_id"])
    assert hotel.status_code == 200, hotel.text
    assert hotel.json() == available_room["hotel"]
    visible = list_rooms(base_url, room["hotel_id"])
    assert visible.status_code == 200, visible.text
    assert visible.json()["total"] == 0
    included = list_rooms(base_url, room["hotel_id"], {"include_archived": True}, access_token=admin_access_token)
    assert included.status_code == 200, included.text
    assert included.json()["items"] == [archived]


@pytest.mark.parametrize("operation", ["update", "availability", "archive"])
@pytest.mark.parametrize("identifier,status,code", [(None, 404, "NOT_FOUND"), ("not-a-uuid", 422, "VALIDATION_ERROR")])
def test_room_mutations_reject_invalid_or_unknown_id(base_url, admin_access_token, operation, identifier, status, code):
    room_id = identifier or str(uuid4())
    if operation == "update":
        response = update_room(base_url, admin_access_token, room_id, BOOKING_ROOM_DATA.copy())
    elif operation == "availability":
        response = update_room_availability(base_url, admin_access_token, room_id, {"is_available": False})
    else:
        response = archive_room(base_url, admin_access_token, room_id)
    assert_api_error(response, status=status, code=code)


@pytest.mark.parametrize("operation", ["update", "availability", "archive"])
@pytest.mark.parametrize("token", [None, "", "invalid-token"], ids=["missing", "empty", "malformed"])
def test_room_mutations_require_valid_token(base_url, available_room, operation, token):
    room = available_room["room"]
    if operation == "update":
        response = update_room(base_url, token, room["id"], BOOKING_ROOM_DATA.copy())
    elif operation == "availability":
        response = update_room_availability(base_url, token, room["id"], {"is_available": False})
    else:
        response = archive_room(base_url, token, room["id"])
    assert_api_error(response, status=401, code="UNAUTHORIZED")
    assert response.headers.get("WWW-Authenticate") == "Bearer"
    saved = get_room(base_url, room["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == room
