from uuid import uuid4

import pytest
from jsonschema import FormatChecker, validate

from api.hotels import archive_hotel, create_hotel
from api.rooms import create_room, get_room, list_rooms
from data.booking import BOOKING_ROOM_DATA
from data.hotels import HOTEL_TEMPLATE
from schemas.room_response import ROOM_SCHEMA
from tests.assertions import assert_api_error


@pytest.mark.parametrize("changes", [
    {"type": kind} for kind in ("single", "double", "twin", "family", "suite")
] + [
    {"room_number": "A"}, {"room_number": "A" * 20},
    {"capacity": 1}, {"capacity": 10},
    {"price_per_night": "0.01"}, {"price_per_night": "9999999999.99"},
])
def test_admin_can_create_room(base_url, admin_access_token, available_room, changes):
    hotel_id = available_room["hotel"]["id"]
    payload = {**BOOKING_ROOM_DATA, "room_number": "202", **changes}
    response = create_room(base_url, admin_access_token, hotel_id, payload)
    assert response.status_code == 201, response.text
    room = response.json()
    validate(room, ROOM_SCHEMA, format_checker=FormatChecker())
    assert room["hotel_id"] == hotel_id
    for field, value in payload.items():
        assert room[field] == value
    assert room["is_available"] is True
    assert room["is_archived"] is False
    assert response.headers.get("X-Request-ID")
    saved = get_room(base_url, room["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == room


@pytest.mark.parametrize("field", tuple(BOOKING_ROOM_DATA))
def test_create_room_requires_all_fields(base_url, admin_access_token, available_room, field):
    payload = {**BOOKING_ROOM_DATA, "room_number": "202"}
    del payload[field]
    response = create_room(base_url, admin_access_token, available_room["hotel"]["id"], payload)
    body = assert_api_error(response, status=422, code="VALIDATION_ERROR")
    assert any(item["field"] == f"body.{field}" for item in body["error"]["details"])
    rooms = list_rooms(base_url, available_room["hotel"]["id"])
    assert rooms.status_code == 200, rooms.text
    assert [room["id"] for room in rooms.json()["items"]] == [available_room["room"]["id"]]
    assert rooms.json()["total"] == 1


@pytest.mark.parametrize("field,value", [
    ("room_number", ""), ("room_number", "x" * 21), ("room_number", 123),
    ("type", "unknown"), ("type", 1),
    ("capacity", 0), ("capacity", 11), ("capacity", True),
    ("capacity", 1.5), ("capacity", "2"),
    ("price_per_night", "0"), ("price_per_night", "-0.01"),
    ("price_per_night", "10000000000.00"), ("price_per_night", "1.001"),
    ("price_per_night", "text"),
] + [(field, None) for field in BOOKING_ROOM_DATA])
def test_create_room_rejects_invalid_fields(base_url, admin_access_token, available_room, field, value):
    payload = {**BOOKING_ROOM_DATA, "room_number": "202", field: value}
    response = create_room(base_url, admin_access_token, available_room["hotel"]["id"], payload)
    body = assert_api_error(response, status=422, code="VALIDATION_ERROR")
    assert any(item["field"] == f"body.{field}" for item in body["error"]["details"])
    rooms = list_rooms(base_url, available_room["hotel"]["id"])
    assert rooms.status_code == 200, rooms.text
    assert rooms.json()["total"] == 1
    assert [room["id"] for room in rooms.json()["items"]] == [available_room["room"]["id"]]


def test_duplicate_room_number_does_not_change_existing_room(base_url, admin_access_token, available_room):
    room = available_room["room"]
    payload = {**BOOKING_ROOM_DATA, "price_per_night": "9876.54"}
    response = create_room(base_url, admin_access_token, room["hotel_id"], payload)
    assert_api_error(response, status=409, code="ROOM_NUMBER_EXISTS")
    saved = get_room(base_url, room["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == room
    rooms = list_rooms(base_url, room["hotel_id"])
    assert rooms.status_code == 200, rooms.text
    assert rooms.json()["total"] == 1


@pytest.mark.parametrize("hotel_state", ["unknown", "invalid_uuid", "archived"])
def test_create_room_rejects_unusable_hotel(base_url, admin_access_token, available_room, hotel_state):
    hotel_id = available_room["hotel"]["id"]
    if hotel_state == "unknown":
        hotel_id = str(uuid4())
    elif hotel_state == "invalid_uuid":
        hotel_id = "not-a-uuid"
    else:
        archived = archive_hotel(base_url, admin_access_token, hotel_id)
        assert archived.status_code == 204, archived.text
    response = create_room(base_url, admin_access_token, hotel_id, {**BOOKING_ROOM_DATA, "room_number": "202"})
    status, code = {"unknown": (404, "NOT_FOUND"), "invalid_uuid": (422, "VALIDATION_ERROR"),
                    "archived": (409, "RESOURCE_ARCHIVED")}[hotel_state]
    assert_api_error(response, status=status, code=code)


def test_room_number_is_unique_only_within_hotel(base_url, admin_access_token, available_room):
    created_hotel = create_hotel(base_url, admin_access_token, {**HOTEL_TEMPLATE, "city": f"Other_{uuid4().hex}"})
    assert created_hotel.status_code == 201, created_hotel.text
    response = create_room(base_url, admin_access_token, created_hotel.json()["id"], BOOKING_ROOM_DATA.copy())
    assert response.status_code == 201, response.text
    assert response.json()["room_number"] == available_room["room"]["room_number"]
    assert response.json()["hotel_id"] != available_room["room"]["hotel_id"]
