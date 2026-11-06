from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from urllib.parse import urlparse
from uuid import uuid4

import allure

from api.bookings import create_booking, get_booking, list_bookings
from api.rooms import get_room_availability
from tests.assertions import assert_api_error


@allure.title("Два одновременных запроса создают одну бронь на один номер")
def test_only_one_concurrent_booking_can_reserve_room(
    base_url, available_room, stay_dates, registered_user, user_access_token,
    second_user, admin_access_token,
):
    room = available_room["room"]
    payload = {"room_id": room["id"], **stay_dates}
    participants = [
        {"id": registered_user["user"]["id"], "token": user_access_token, "key": uuid4().hex},
        {"id": second_user["id"], "token": second_user["access_token"], "key": uuid4().hex},
    ]
    assert participants[0]["id"] != participants[1]["id"]
    assert participants[0]["key"] != participants[1]["key"]

    with allure.step("Проверить исходную доступность номера и пустые списки"):
        for participant in participants:
            before = list_bookings(base_url, participant["token"])
            assert before.status_code == 200, before.text
            assert before.json()["total"] == 0
            assert before.json()["items"] == []
        initial = get_room_availability(base_url, room["id"], stay_dates)
        assert initial.status_code == 200, initial.text
        assert initial.json()["available"] is True
        assert initial.json()["reason"] is None

    with allure.step("Отправить два запроса и проверить успех и конфликт"):
        barrier = Barrier(2, timeout=10)

        def reserve(participant):
            barrier.wait()
            # Each call uses its own requests session and payload; no automatic retries.
            return create_booking(base_url, participant["token"], payload.copy(), participant["key"])

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(reserve, participant) for participant in participants]
            responses = [future.result(timeout=30) for future in futures]

        diagnostics = [(response.status_code, response.text) for response in responses]
        assert sorted(response.status_code for response in responses) == [201, 409], diagnostics
        winner_index = next(index for index, response in enumerate(responses) if response.status_code == 201)
        loser_index = 1 - winner_index
        created = responses[winner_index]
        rejected = responses[loser_index]
        winner = participants[winner_index]
        assert_api_error(rejected, status=409, code="ROOM_NOT_AVAILABLE")
        assert created.headers.get("X-Request-ID")
        assert created.headers.get("Idempotency-Replayed", "").lower() == "false"
        booking = created.json()
        assert booking["user_id"] == winner["id"]
        assert booking["status"] == "pending_payment"
        for field, value in payload.items():
            assert booking[field] == value

    with allure.step("Убедиться, что сохранилась одна бронь и номер занят"):
        # Status codes alone cannot prove there was only one committed booking.
        for index, participant in enumerate(participants):
            listed = list_bookings(base_url, participant["token"])
            assert listed.status_code == 200, listed.text
            expected_items = [booking] if index == winner_index else []
            assert listed.json()["total"] == len(expected_items)
            assert listed.json()["items"] == expected_items
        admin_list = list_bookings(base_url, admin_access_token, {"hotel_id": available_room["hotel"]["id"]})
        assert admin_list.status_code == 200, admin_list.text
        assert admin_list.json()["total"] == 1
        assert admin_list.json()["items"] == [booking]
        saved = get_booking(base_url, winner["token"], booking["id"])
        assert saved.status_code == 200, saved.text
        assert saved.json() == booking
        occupied = get_room_availability(base_url, room["id"], stay_dates)
        assert occupied.status_code == 200, occupied.text
        assert occupied.json()["available"] is False
        assert occupied.json()["reason"] == "ROOM_NOT_AVAILABLE"


def test_concurrent_same_key_returns_one_booking(
    base_url, available_room, stay_dates, registered_user, user_access_token, admin_access_token,
):
    room = available_room["room"]
    payload = {"room_id": room["id"], **stay_dates}
    key = uuid4().hex
    before = list_bookings(base_url, user_access_token)
    assert before.status_code == 200, before.text
    assert before.json()["total"] == 0
    assert before.json()["items"] == []
    barrier = Barrier(2, timeout=10)

    def reserve():
        barrier.wait()
        return create_booking(base_url, user_access_token, payload.copy(), key)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(reserve) for _ in range(2)]
        responses = [future.result(timeout=30) for future in futures]

    diagnostics = [(response.status_code, response.text) for response in responses]
    assert [response.status_code for response in responses] == [201, 201], diagnostics
    booking = responses[0].json()
    assert responses[1].json() == booking
    assert booking["user_id"] == registered_user["user"]["id"]
    assert booking["status"] == "pending_payment"
    for field, value in payload.items():
        assert booking[field] == value
    assert sorted(response.headers.get("Idempotency-Replayed", "").lower() for response in responses) == ["false", "true"]
    location = responses[0].headers.get("Location")
    assert location
    assert responses[1].headers.get("Location") == location
    assert urlparse(location).path == f"{urlparse(base_url).path}/bookings/{booking['id']}"
    for response in responses:
        assert response.headers.get("X-Request-ID")

    # A later replay must retain the original snapshot, including its expiry time.
    replay = create_booking(base_url, user_access_token, payload.copy(), key)
    assert replay.status_code == 201, replay.text
    assert replay.json() == booking
    assert replay.headers.get("Idempotency-Replayed", "").lower() == "true"
    assert replay.headers.get("Location") == location

    for token, params in (
        (user_access_token, None),
        (admin_access_token, {"hotel_id": available_room["hotel"]["id"]}),
    ):
        listed = list_bookings(base_url, token, params)
        assert listed.status_code == 200, listed.text
        assert listed.json()["total"] == 1
        assert listed.json()["items"] == [booking]
        saved = get_booking(base_url, token, booking["id"])
        assert saved.status_code == 200, saved.text
        assert saved.json() == booking
    occupied = get_room_availability(base_url, room["id"], stay_dates)
    assert occupied.status_code == 200, occupied.text
    assert occupied.json()["available"] is False
    assert occupied.json()["reason"] == "ROOM_NOT_AVAILABLE"
