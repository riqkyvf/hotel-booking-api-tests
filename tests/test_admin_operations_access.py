from uuid import uuid4

import allure
import pytest

from api.hotels import archive_hotel, create_hotel, get_hotel, list_hotels, update_hotel
from api.rooms import (
    archive_room, create_room, get_room, list_rooms, update_room, update_room_availability,
)
from api.users import get_profile, get_user_as_admin, list_users_as_admin, update_user_as_admin
from data.booking import BOOKING_ROOM_DATA
from data.hotels import HOTEL_TEMPLATE
from tests.assertions import assert_api_error


@pytest.fixture
def ordinary_user_profile(base_url, user_access_token):
    response = get_profile(base_url, user_access_token)
    assert response.status_code == 200, response.text
    profile = response.json()
    assert profile["role"] == "user"
    assert profile["is_active"] is True
    return profile


@pytest.mark.smoke
@pytest.mark.usefixtures("ordinary_user_profile")
@allure.title("Обычный пользователь не может создать отель")
def test_user_cannot_create_hotel(base_url, user_access_token):
    city = f"Forbidden_{uuid4().hex}"
    payload = {**HOTEL_TEMPLATE, "city": city}
    before = list_hotels(base_url, {"city": city})
    assert before.status_code == 200, before.text
    assert before.json()["total"] == 0

    response = create_hotel(base_url, user_access_token, payload)
    assert_api_error(response, status=403, code="FORBIDDEN")

    after = list_hotels(base_url, {"city": city})
    assert after.status_code == 200, after.text
    assert after.json()["total"] == 0
    assert after.json()["items"] == []


@pytest.mark.parametrize("operation", ["update", "archive"])
@pytest.mark.usefixtures("ordinary_user_profile")
def test_user_cannot_modify_hotel(
    base_url, user_access_token, available_room, operation,
):
    hotel = available_room["hotel"]
    room = available_room["room"]
    if operation == "update":
        payload = {field: hotel[field] for field in HOTEL_TEMPLATE}
        payload["name"] = "Must Not Be Saved"
        response = update_hotel(base_url, user_access_token, hotel["id"], payload)
    else:
        response = archive_hotel(base_url, user_access_token, hotel["id"])
    assert_api_error(response, status=403, code="FORBIDDEN")

    saved_hotel = get_hotel(base_url, hotel["id"])
    assert saved_hotel.status_code == 200, saved_hotel.text
    assert saved_hotel.json() == hotel
    saved_room = get_room(base_url, room["id"])
    assert saved_room.status_code == 200, saved_room.text
    assert saved_room.json() == room


@pytest.mark.usefixtures("ordinary_user_profile")
def test_user_cannot_create_room(base_url, user_access_token, available_room):
    hotel = available_room["hotel"]
    room = available_room["room"]
    payload = {**BOOKING_ROOM_DATA, "room_number": "102"}
    before = list_rooms(base_url, hotel["id"])
    assert before.status_code == 200, before.text
    assert before.json()["total"] == 1
    assert [item["id"] for item in before.json()["items"]] == [room["id"]]

    response = create_room(base_url, user_access_token, hotel["id"], payload)
    assert_api_error(response, status=403, code="FORBIDDEN")

    after = list_rooms(base_url, hotel["id"])
    assert after.status_code == 200, after.text
    assert after.json() == before.json()


@pytest.mark.parametrize("operation", ["update", "disable", "archive"])
@pytest.mark.usefixtures("ordinary_user_profile")
def test_user_cannot_modify_room(
    base_url, user_access_token, available_room, operation,
):
    room = available_room["room"]
    if operation == "update":
        payload = {field: room[field] for field in BOOKING_ROOM_DATA}
        payload["price_per_night"] = "2345.67"
        response = update_room(base_url, user_access_token, room["id"], payload)
    elif operation == "disable":
        response = update_room_availability(base_url, user_access_token, room["id"], {"is_available": False})
    else:
        response = archive_room(base_url, user_access_token, room["id"])
    assert_api_error(response, status=403, code="FORBIDDEN")

    saved_room = get_room(base_url, room["id"])
    assert saved_room.status_code == 200, saved_room.text
    assert saved_room.json() == room


def test_user_cannot_list_users_as_admin(
    base_url, user_access_token, ordinary_user_profile, admin_access_token,
):
    response = list_users_as_admin(base_url, user_access_token)
    assert_api_error(response, status=403, code="FORBIDDEN")
    assert ordinary_user_profile["email"] not in response.text

    control = list_users_as_admin(base_url, admin_access_token)
    assert control.status_code == 200, control.text
    assert isinstance(control.json()["items"], list)


@pytest.mark.parametrize("target", ["self", "other"])
def test_user_cannot_read_user_as_admin(
    base_url, user_access_token, ordinary_user_profile, second_user, admin_access_token, target,
):
    target_id = ordinary_user_profile["id"] if target == "self" else second_user["id"]
    response = get_user_as_admin(base_url, user_access_token, target_id)
    assert_api_error(response, status=403, code="FORBIDDEN")

    control = get_user_as_admin(base_url, admin_access_token, target_id)
    assert control.status_code == 200, control.text
    assert control.json()["id"] == target_id
    assert control.json()["role"] == "user"
    assert control.json()["is_active"] is True


@pytest.mark.parametrize("target", ["self", "other"])
@pytest.mark.parametrize("change", [{"role": "admin"}, {"is_active": False}], ids=["promote", "disable"])
def test_user_cannot_change_role_or_activity_as_admin(
    base_url, user_access_token, ordinary_user_profile, second_user, admin_access_token, target, change,
):
    target_id = ordinary_user_profile["id"] if target == "self" else second_user["id"]
    before = get_user_as_admin(base_url, admin_access_token, target_id)
    assert before.status_code == 200, before.text
    assert before.json()["role"] == "user"
    assert before.json()["is_active"] is True

    response = update_user_as_admin(base_url, user_access_token, target_id, change)
    assert_api_error(response, status=403, code="FORBIDDEN")

    saved_user = get_user_as_admin(base_url, admin_access_token, target_id)
    assert saved_user.status_code == 200, saved_user.text
    assert saved_user.json() == before.json()
    target_token = user_access_token if target == "self" else second_user["access_token"]
    profile = get_profile(base_url, target_token)
    assert profile.status_code == 200, profile.text
    assert profile.json() == before.json()
