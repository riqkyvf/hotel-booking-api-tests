from uuid import uuid4

import pytest
from jsonschema import validate

from api.bookings import get_booking
from api.hotels import archive_hotel, create_hotel, get_hotel, list_hotels, update_hotel
from api.payments import get_payment
from api.rooms import get_room, list_rooms
from data.hotels import HOTEL_TEMPLATE
from schemas.hotel_response import HOTEL_SCHEMA
from tests.assertions import assert_api_error


@pytest.fixture
def hotel_operation(base_url, admin_access_token, available_room, request):
    """Prepare a target and expose either POST or PUT with the same HotelInput."""
    hotel = available_room["hotel"]

    def send(payload=None, *, raw_body=None):
        if request.param == "create":
            return create_hotel(base_url, admin_access_token, payload, raw_body=raw_body)
        return update_hotel(base_url, admin_access_token, hotel["id"], payload, raw_body=raw_body)

    return {"send": send, "hotel": hotel, "operation": request.param}


@pytest.mark.parametrize("hotel_operation", ["create", "update"], indirect=True)
@pytest.mark.parametrize("changes", [
    {}, {"name": "x"}, {"name": "x" * 150},
    {"city": "x"}, {"city": "x" * 100},
    {"address": "x"}, {"address": "x" * 250},
    {"description": ""}, {"description": "x" * 5000},
    {"rating": "0.0"}, {"rating": "5.0"},
])
def test_admin_can_create_and_update_hotel(base_url, hotel_operation, changes):
    original = hotel_operation["hotel"]
    payload = {**HOTEL_TEMPLATE, "name": f"Changed_{uuid4().hex}", "city": f"New_{uuid4().hex}", **changes}
    response = hotel_operation["send"](payload)
    assert response.status_code == (201 if hotel_operation["operation"] == "create" else 200), response.text
    hotel = response.json()
    validate(hotel, HOTEL_SCHEMA)
    for field, value in payload.items():
        assert hotel[field] == value
    assert hotel["is_archived"] is False
    assert response.headers.get("X-Request-ID")
    if hotel_operation["operation"] == "update":
        assert hotel["id"] == original["id"]
        assert hotel["created_at"] == original["created_at"]
    else:
        assert hotel["id"] != original["id"]
    saved = get_hotel(base_url, hotel["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == hotel


@pytest.mark.parametrize("hotel_operation", ["create", "update"], indirect=True)
@pytest.mark.parametrize("field", tuple(HOTEL_TEMPLATE))
def test_hotel_requires_full_input(base_url, hotel_operation, field):
    payload = {**HOTEL_TEMPLATE}
    del payload[field]
    response = hotel_operation["send"](payload)
    body = assert_api_error(response, status=422, code="VALIDATION_ERROR")
    assert any(item["field"] == f"body.{field}" for item in body["error"]["details"])
    saved = get_hotel(base_url, hotel_operation["hotel"]["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == hotel_operation["hotel"]


@pytest.mark.parametrize("hotel_operation", ["create", "update"], indirect=True)
@pytest.mark.parametrize("field,value", [
    ("name", ""), ("name", "x" * 151), ("city", ""), ("city", "x" * 101),
    ("address", ""), ("address", "x" * 251), ("description", "x" * 5001),
    ("rating", "-0.1"), ("rating", "5.1"), ("rating", "4.55"), ("rating", "text"),
    ("name", 123), ("description", True),
] + [(field, None) for field in HOTEL_TEMPLATE])
def test_hotel_rejects_invalid_fields(base_url, hotel_operation, field, value):
    payload = {**HOTEL_TEMPLATE, field: value}
    response = hotel_operation["send"](payload)
    body = assert_api_error(response, status=422, code="VALIDATION_ERROR")
    assert any(item["field"] == f"body.{field}" for item in body["error"]["details"])
    saved = get_hotel(base_url, hotel_operation["hotel"]["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == hotel_operation["hotel"]


@pytest.mark.parametrize("hotel_operation", ["create", "update"], indirect=True)
@pytest.mark.parametrize("field,value", [("is_archived", True), ("id", str(uuid4())), ("unexpected", "x")])
def test_hotel_rejects_read_only_or_unknown_fields(base_url, hotel_operation, field, value):
    response = hotel_operation["send"]({**HOTEL_TEMPLATE, "name": "Must Not Save", field: value})
    body = assert_api_error(response, status=422, code="VALIDATION_ERROR")
    assert any(item["field"] == f"body.{field}" for item in body["error"]["details"])
    saved = get_hotel(base_url, hotel_operation["hotel"]["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == hotel_operation["hotel"]


@pytest.mark.parametrize("hotel_operation", ["create", "update"], indirect=True)
@pytest.mark.parametrize("raw_body", ['{"name":', "[]"], ids=["malformed_json", "array"])
def test_hotel_rejects_invalid_json_body(base_url, hotel_operation, raw_body):
    response = hotel_operation["send"](raw_body=raw_body)
    assert_api_error(response, status=422, code="VALIDATION_ERROR")
    saved = get_hotel(base_url, hotel_operation["hotel"]["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == hotel_operation["hotel"]


def test_hotel_update_does_not_change_its_room(base_url, admin_access_token, available_room):
    hotel = available_room["hotel"]
    room = available_room["room"]
    updated = update_hotel(base_url, admin_access_token, hotel["id"], {
        **HOTEL_TEMPLATE, "name": "Updated hotel", "city": f"Updated_{uuid4().hex}",
    })
    assert updated.status_code == 200, updated.text
    saved_room = get_room(base_url, room["id"])
    assert saved_room.status_code == 200, saved_room.text
    assert saved_room.json() == room


def test_archive_hotel_archives_rooms_and_is_repeatable(base_url, admin_access_token, available_room):
    hotel = available_room["hotel"]
    room = available_room["room"]
    response = archive_hotel(base_url, admin_access_token, hotel["id"])
    assert response.status_code == 204, response.text
    assert response.content == b""
    public_hotel = get_hotel(base_url, hotel["id"])
    assert_api_error(public_hotel, status=404, code="NOT_FOUND")
    public_room = get_room(base_url, room["id"])
    assert_api_error(public_room, status=404, code="NOT_FOUND")
    saved_hotel = get_hotel(base_url, hotel["id"], access_token=admin_access_token)
    assert saved_hotel.status_code == 200, saved_hotel.text
    archived_hotel = saved_hotel.json()
    assert archived_hotel["is_archived"] is True
    for field in (*HOTEL_TEMPLATE, "id", "created_at"):
        assert archived_hotel[field] == hotel[field]
    saved_room = get_room(base_url, room["id"], access_token=admin_access_token)
    assert saved_room.status_code == 200, saved_room.text
    archived_room = saved_room.json()
    assert archived_room["is_archived"] is True
    for field in ("id", "hotel_id", "room_number", "type", "capacity", "price_per_night", "created_at"):
        assert archived_room[field] == room[field]
    # Repeated DELETE must preserve both final snapshots.
    repeated = archive_hotel(base_url, admin_access_token, hotel["id"])
    assert repeated.status_code == 204, repeated.text
    assert repeated.content == b""
    for response, expected in (
        (get_hotel(base_url, hotel["id"], access_token=admin_access_token), archived_hotel),
        (get_room(base_url, room["id"], access_token=admin_access_token), archived_room),
    ):
        assert response.status_code == 200, response.text
        assert response.json() == expected
    catalog = list_hotels(base_url, {"city": hotel["city"]})
    assert catalog.status_code == 200, catalog.text
    assert catalog.json()["items"] == []
    rooms = list_rooms(base_url, hotel["id"], {"include_archived": True}, access_token=admin_access_token)
    assert rooms.status_code == 200, rooms.text
    assert [item["id"] for item in rooms.json()["items"]] == [room["id"]]


def test_archived_hotel_cannot_be_updated(base_url, admin_access_token, available_room):
    hotel_id = available_room["hotel"]["id"]
    archived = archive_hotel(base_url, admin_access_token, hotel_id)
    assert archived.status_code == 204, archived.text
    before = get_hotel(base_url, hotel_id, access_token=admin_access_token)
    assert before.status_code == 200, before.text
    response = update_hotel(base_url, admin_access_token, hotel_id, {**HOTEL_TEMPLATE, "name": "Must Not Save"})
    assert_api_error(response, status=409, code="RESOURCE_ARCHIVED")
    saved = get_hotel(base_url, hotel_id, access_token=admin_access_token)
    assert saved.status_code == 200, saved.text
    assert saved.json() == before.json()


def test_hotel_with_active_booking_cannot_be_archived(
    base_url, admin_access_token, user_access_token, available_room, booking_with_payment,
):
    hotel = available_room["hotel"]
    room = available_room["room"]
    response = archive_hotel(base_url, admin_access_token, hotel["id"])
    assert_api_error(response, status=409, code="ACTIVE_BOOKINGS_EXIST")
    for saved, expected in (
        (get_hotel(base_url, hotel["id"]), hotel),
        (get_room(base_url, room["id"]), room),
        (get_booking(base_url, user_access_token, booking_with_payment["booking"]["id"]), booking_with_payment["booking"]),
        (get_payment(base_url, user_access_token, booking_with_payment["payment"]["id"]), booking_with_payment["payment"]),
    ):
        assert saved.status_code == 200, saved.text
        assert saved.json() == expected


@pytest.mark.parametrize("operation", ["update", "archive"])
@pytest.mark.parametrize("identifier,status,code", [(None, 404, "NOT_FOUND"), ("not-a-uuid", 422, "VALIDATION_ERROR")])
def test_hotel_mutations_reject_unknown_or_invalid_id(base_url, admin_access_token, operation, identifier, status, code):
    hotel_id = identifier or str(uuid4())
    response = (update_hotel(base_url, admin_access_token, hotel_id, HOTEL_TEMPLATE.copy())
                if operation == "update" else archive_hotel(base_url, admin_access_token, hotel_id))
    assert_api_error(response, status=status, code=code)


@pytest.mark.parametrize("operation", ["update", "archive"])
@pytest.mark.parametrize("token", [None, "invalid-token"], ids=["missing", "malformed"])
def test_hotel_mutations_require_authorization(base_url, available_room, operation, token):
    hotel = available_room["hotel"]
    response = (update_hotel(base_url, token, hotel["id"], {**HOTEL_TEMPLATE, "name": "Must Not Save"})
                if operation == "update" else archive_hotel(base_url, token, hotel["id"]))
    assert_api_error(response, status=401, code="UNAUTHORIZED")
    assert response.headers.get("WWW-Authenticate") == "Bearer"
    saved = get_hotel(base_url, hotel["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == hotel
