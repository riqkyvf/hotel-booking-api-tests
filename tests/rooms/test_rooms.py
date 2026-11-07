from uuid import uuid4

import pytest
from jsonschema import FormatChecker, validate

from api.hotels import archive_hotel, create_hotel
from api.rooms import archive_room, create_room, get_room, list_rooms, update_room_availability
from data.hotels import HOTEL_TEMPLATE
from schemas.room_response import ROOM_SCHEMA
from tests.assertions import assert_api_error


@pytest.fixture
def room_catalog(base_url, admin_access_token):
    created = create_hotel(base_url, admin_access_token, {**HOTEL_TEMPLATE, "city": f"Rooms_{uuid4().hex}"})
    assert created.status_code == 201, created.text
    hotel = created.json()
    cases = {
        "a": ("2", "double", 2, "1000.00"),
        "b": ("10", "single", 1, "500.00"),
        "c": ("3", "suite", 4, "1000.00"),
        "d": ("20", "double", 2, "1000.00"),
        "archived": ("99", "family", 5, "100.00"),
    }
    rooms = {}
    for key, (number, kind, capacity, price) in cases.items():
        response = create_room(base_url, admin_access_token, hotel["id"], {
            "room_number": number, "type": kind, "capacity": capacity, "price_per_night": price,
        })
        assert response.status_code == 201, response.text
        rooms[key] = response.json()
    disabled = update_room_availability(base_url, admin_access_token, rooms["d"]["id"], {"is_available": False})
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["is_available"] is False
    rooms["d"] = disabled.json()
    archived = archive_room(base_url, admin_access_token, rooms["archived"]["id"])
    assert archived.status_code == 204, archived.text
    return {"hotel": hotel, "rooms": rooms}


@pytest.mark.parametrize("params,keys", [
    ({"min_price": "1000"}, ("a", "c", "d")),
    ({"max_price": "500"}, ("b",)),
    ({"min_price": "1000", "max_price": "1000"}, ("a", "c", "d")),
    ({"min_capacity": 2}, ("a", "c", "d")),
    ({"min_capacity": 10}, ()),
    ({"type": "double"}, ("a", "d")),
    ({"type": "family"}, ()),
    ({"min_price": "1000", "max_price": "1000", "min_capacity": 3, "type": "suite"}, ("c",)),
])
def test_room_list_filters(base_url, room_catalog, params, keys):
    response = list_rooms(base_url, room_catalog["hotel"]["id"], params)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == len(keys)
    assert {room["id"] for room in body["items"]} == {room_catalog["rooms"][key]["id"] for key in keys}
    assert len(body["items"]) == len(keys)
    for room in body["items"]:
        validate(room, ROOM_SCHEMA, format_checker=FormatChecker())
        assert room["hotel_id"] == room_catalog["hotel"]["id"]
        assert room["is_archived"] is False


@pytest.mark.parametrize("sort", [None, "price", "-price", "capacity", "-capacity", "room_number", "-room_number"])
def test_room_list_sorting(base_url, room_catalog, sort):
    rooms = room_catalog["rooms"]
    tied_price = sorted(rooms[key]["id"] for key in ("a", "c", "d"))
    tied_capacity = sorted(rooms[key]["id"] for key in ("a", "d"))
    expected = {
        None: [rooms["b"]["id"], *tied_price],
        "price": [rooms["b"]["id"], *tied_price],
        "-price": [*tied_price, rooms["b"]["id"]],
        "capacity": [rooms["b"]["id"], *tied_capacity, rooms["c"]["id"]],
        "-capacity": [rooms["c"]["id"], *tied_capacity, rooms["b"]["id"]],
        "room_number": [rooms[key]["id"] for key in ("b", "a", "d", "c")],
        "-room_number": [rooms[key]["id"] for key in ("c", "d", "a", "b")],
    }[sort]
    params = {} if sort is None else {"sort": sort}
    response = list_rooms(base_url, room_catalog["hotel"]["id"], params)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 4
    assert [room["id"] for room in body["items"]] == expected
    assert response.headers.get("X-Request-ID")
    if sort is None:
        assert body["limit"] == 20
        assert body["offset"] == 0


@pytest.mark.parametrize("limit,offset", [(1, 0), (2, 0), (2, 2), (100, 0), (2, 4), (2, 10)])
def test_room_list_pagination(base_url, room_catalog, limit, offset):
    expected = [room_catalog["rooms"][key]["id"] for key in ("b", "a", "d", "c")]
    response = list_rooms(base_url, room_catalog["hotel"]["id"], {"sort": "room_number", "limit": limit, "offset": offset})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 4
    assert body["limit"] == limit
    assert body["offset"] == offset
    assert [room["id"] for room in body["items"]] == expected[offset:offset + limit]


@pytest.mark.parametrize("params", [
    {"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "text"},
    {"min_price": "-0.01"}, {"max_price": "text"},
    {"min_capacity": 0}, {"min_capacity": 11}, {"min_capacity": "text"},
    {"type": "unknown"}, {"include_archived": "unknown"},
])
def test_room_list_rejects_invalid_query(base_url, available_room, params):
    response = list_rooms(base_url, available_room["hotel"]["id"], params)
    body = assert_api_error(response, status=422, code="VALIDATION_ERROR")
    field = next(iter(params))
    assert any(item["field"] == f"query.{field}" for item in body["error"]["details"])


@pytest.mark.parametrize("params,code", [
    ({"sort": "unknown"}, "INVALID_SORT"), ({"sort": "--price"}, "INVALID_SORT"),
    ({"min_price": "1000", "max_price": "500"}, "INVALID_FILTER_RANGE"),
])
def test_room_list_rejects_invalid_sort_and_range(base_url, available_room, params, code):
    response = list_rooms(base_url, available_room["hotel"]["id"], params)
    assert_api_error(response, status=422, code=code)


@pytest.mark.parametrize("role", ["guest", "user", "admin"])
def test_room_details_and_disabled_room_are_visible(base_url, room_catalog, user_access_token, admin_access_token, role):
    token = {"guest": None, "user": user_access_token, "admin": admin_access_token}[role]
    room = room_catalog["rooms"]["d"]
    response = get_room(base_url, room["id"], access_token=token)
    assert response.status_code == 200, response.text
    validate(response.json(), ROOM_SCHEMA, format_checker=FormatChecker())
    assert response.json() == room
    assert response.headers.get("X-Request-ID")
    listed = list_rooms(base_url, room_catalog["hotel"]["id"], access_token=token)
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] == 4
    assert room["id"] in {item["id"] for item in listed.json()["items"]}


@pytest.mark.parametrize("role", ["guest", "user", "admin"])
@pytest.mark.parametrize("archived_parent", [False, True], ids=["room_archived", "hotel_archived"])
def test_archived_room_read_access(base_url, room_catalog, user_access_token, admin_access_token, role, archived_parent):
    hotel_id = room_catalog["hotel"]["id"]
    if archived_parent:
        archived = archive_hotel(base_url, admin_access_token, hotel_id)
        assert archived.status_code == 204, archived.text
    room_id = room_catalog["rooms"]["a" if archived_parent else "archived"]["id"]
    token = {"guest": None, "user": user_access_token, "admin": admin_access_token}[role]
    response = get_room(base_url, room_id, access_token=token)
    if role == "admin":
        assert response.status_code == 200, response.text
        validate(response.json(), ROOM_SCHEMA, format_checker=FormatChecker())
        assert response.json()["id"] == room_id
        assert response.json()["is_archived"] is True
    else:
        assert_api_error(response, status=404, code="NOT_FOUND")
    listed = list_rooms(base_url, hotel_id, access_token=token)
    if archived_parent and role != "admin":
        assert_api_error(listed, status=404, code="NOT_FOUND")
    else:
        assert listed.status_code == 200, listed.text
        assert listed.json()["total"] == (0 if archived_parent else 4)
        assert room_id not in {room["id"] for room in listed.json()["items"]}
    included = list_rooms(base_url, hotel_id, {"include_archived": True}, access_token=token)
    if role != "admin":
        assert_api_error(included, status=403, code="FORBIDDEN")
    else:
        assert included.status_code == 200, included.text
        assert included.json()["total"] == 5
        assert {room["id"] for room in included.json()["items"]} == {room["id"] for room in room_catalog["rooms"].values()}


@pytest.mark.parametrize("resource", ["room", "hotel"])
@pytest.mark.parametrize("identifier,status,code", [
    ("not-a-uuid", 422, "VALIDATION_ERROR"), (None, 404, "NOT_FOUND"),
])
def test_read_rooms_rejects_invalid_or_unknown_id(base_url, resource, identifier, status, code):
    identifier = identifier or str(uuid4())
    response = get_room(base_url, identifier) if resource == "room" else list_rooms(base_url, identifier)
    assert_api_error(response, status=status, code=code)
