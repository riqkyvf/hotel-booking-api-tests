from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from api.bookings import cancel_booking, create_booking, get_booking, list_bookings
from api.hotels import create_hotel
from api.payments import create_payment, simulate_payment_success
from api.rooms import create_room
from data.booking import BOOKING_ROOM_DATA
from data.hotels import HOTEL_TEMPLATE
from db import move_booking_expiry_to_past
from tests.assertions import assert_api_error


@pytest.fixture
def booking_catalog(base_url, admin_access_token, registered_user, user_access_token, second_user):
    """Four owner bookings across two hotels, plus another user's booking in the first hotel."""
    hotels, rooms = [], []
    for price in ("1000.00", "2000.00"):
        created = create_hotel(base_url, admin_access_token, {**HOTEL_TEMPLATE, "city": f"BookingList_{uuid4().hex}"})
        assert created.status_code == 201, created.text
        hotels.append(created.json())
        created_room = create_room(base_url, admin_access_token, hotels[-1]["id"],
                                   {**BOOKING_ROOM_DATA, "price_per_night": price})
        assert created_room.status_code == 201, created_room.text
        rooms.append(created_room.json())
    # b has a separate room/price but the same total as a, exercising UUID tie-breaking.
    created_room = create_room(base_url, admin_access_token, hotels[0]["id"],
                               {**BOOKING_ROOM_DATA, "room_number": "102", "price_per_night": "500.00"})
    assert created_room.status_code == 201, created_room.text
    rooms.append(created_room.json())
    today = datetime.now(timezone.utc).date()
    bookings = {}
    for key, room_index, offset, nights, status in (
        ("a", 0, 2, 1, "pending_payment"), ("b", 2, 4, 2, "confirmed"),
        ("c", 1, 4, 1, "cancelled"), ("d", 1, 7, 1, "pending_payment"),
    ):
        check_in = today + timedelta(days=offset)
        response = create_booking(base_url, user_access_token, {
            "room_id": rooms[room_index]["id"], "check_in": check_in.isoformat(),
            "check_out": (check_in + timedelta(days=nights)).isoformat(), "guests": 2,
        }, uuid4().hex)
        assert response.status_code == 201, response.text
        booking = response.json()
        if status == "confirmed":
            payment = create_payment(base_url, user_access_token, booking["id"])
            assert payment.status_code == 201, payment.text
            paid = simulate_payment_success(base_url, user_access_token, payment.json()["id"])
            assert paid.status_code == 200, paid.text
        elif status == "cancelled":
            cancelled = cancel_booking(base_url, user_access_token, booking["id"])
            assert cancelled.status_code == 200, cancelled.text
        saved = get_booking(base_url, user_access_token, booking["id"])
        assert saved.status_code == 200, saved.text
        assert saved.json()["status"] == status
        bookings[key] = saved.json()
    other_date = today + timedelta(days=15)
    other = create_booking(base_url, second_user["access_token"], {
        "room_id": rooms[0]["id"], "check_in": other_date.isoformat(),
        "check_out": (other_date + timedelta(days=1)).isoformat(), "guests": 2,
    }, uuid4().hex)
    assert other.status_code == 201, other.text
    return {"bookings": bookings, "hotels": hotels, "today": today,
            "owner_id": registered_user["user"]["id"], "other": other.json()}


def reader_options(reader, catalog, user_token, admin_token):
    # Admin results are scoped to this test's user; no assumptions about the shared seed.
    return ((user_token, {}) if reader == "owner"
            else (admin_token, {"user_id": catalog["owner_id"]}))


@pytest.mark.parametrize("case,keys", [
    ("pending", ("a", "d")), ("confirmed", ("b",)), ("cancelled", ("c",)),
    ("expired", ()), ("completed", ()), ("first_hotel", ("a", "b")), ("second_hotel", ("c", "d")),
    ("from", ("b", "c", "d")), ("to", ("a", "b", "c")), ("same_day", ("b", "c")),
    ("status_hotel", ("d",)), ("status_date", ("b",)),
])
def test_booking_list_filters(base_url, user_access_token, booking_catalog, case, keys):
    catalog = booking_catalog
    boundary = (catalog["today"] + timedelta(days=4)).isoformat()
    filters = {
        "pending": {"status": "pending_payment"}, "confirmed": {"status": "confirmed"},
        "cancelled": {"status": "cancelled"}, "expired": {"status": "expired"}, "completed": {"status": "completed"},
        "first_hotel": {"hotel_id": catalog["hotels"][0]["id"]},
        "second_hotel": {"hotel_id": catalog["hotels"][1]["id"]},
        "from": {"check_in_from": boundary}, "to": {"check_in_to": boundary},
        "same_day": {"check_in_from": boundary, "check_in_to": boundary},
        "status_hotel": {"status": "pending_payment", "hotel_id": catalog["hotels"][1]["id"]},
        "status_date": {"status": "confirmed", "check_in_from": boundary, "check_in_to": boundary},
    }[case]
    response = list_bookings(base_url, user_access_token, filters)
    assert response.status_code == 200, response.text
    page = response.json()
    assert page["total"] == len(keys)
    assert len(page["items"]) == len(keys)
    expected = {catalog["bookings"][key]["id"]: catalog["bookings"][key] for key in keys}
    assert {item["id"] for item in page["items"]} == set(expected)
    for item in page["items"]:
        assert item == expected[item["id"]]
        assert item["user_id"] == catalog["owner_id"]
    assert response.headers.get("X-Request-ID")


def test_admin_filters_bookings_by_owner_hotel_and_status(base_url, admin_access_token, booking_catalog):
    response = list_bookings(base_url, admin_access_token, {
        "user_id": booking_catalog["owner_id"],
        "hotel_id": booking_catalog["hotels"][0]["id"],
        "status": "pending_payment",
    })

    assert response.status_code == 200, response.text
    page = response.json()
    assert page["total"] == 1
    assert page["items"] == [booking_catalog["bookings"]["a"]]


@pytest.mark.db
@pytest.mark.parametrize("reader", ["owner", "admin"])
def test_booking_list_returns_expired_booking(
    base_url, database_url, user_access_token, admin_access_token, booking_catalog, reader,
):
    original = booking_catalog["bookings"]["a"]
    expires_at = move_booking_expiry_to_past(database_url, original["id"], original["user_id"])
    token, scope = reader_options(reader, booking_catalog, user_access_token, admin_access_token)

    response = list_bookings(base_url, token, {**scope, "status": "expired"})

    assert response.status_code == 200, response.text
    assert response.headers.get("X-Request-ID")
    page = response.json()
    assert page["total"] == 1
    assert [item["id"] for item in page["items"]] == [original["id"]]
    expired = page["items"][0]
    assert expired["status"] == "expired"
    assert datetime.fromisoformat(expired["expires_at"]) == expires_at

    saved = get_booking(base_url, token, original["id"])
    assert saved.status_code == 200, saved.text
    assert saved.json() == expired


@pytest.mark.parametrize("reader,sort", [
    ("owner", None), ("owner", "created_at"), ("owner", "-created_at"),
    ("owner", "check_in"), ("owner", "-check_in"), ("owner", "total_price"),
    ("owner", "-total_price"), ("admin", "-total_price"),
])
def test_booking_list_sorting(base_url, user_access_token, admin_access_token, booking_catalog, reader, sort):
    token, scope = reader_options(reader, booking_catalog, user_access_token, admin_access_token)
    params = scope if sort is None else {**scope, "sort": sort}
    response = list_bookings(base_url, token, params)
    assert response.status_code == 200, response.text
    actual_sort = sort or "-created_at"
    field = actual_sort.lstrip("-")
    records = booking_catalog["bookings"]
    # Explicit equality groups independently exercise price and date ordering.
    tied_prices = {group: sorted(records[key]["id"] for key in group) for group in ("ab", "cd")}
    tied_dates = sorted(records[key]["id"] for key in "bc")
    if field == "total_price":
        expected = (tied_prices["cd"] + tied_prices["ab"] if actual_sort.startswith("-")
                    else tied_prices["ab"] + tied_prices["cd"])
    elif field == "check_in":
        expected = ([records["d"]["id"], *tied_dates, records["a"]["id"]] if actual_sort.startswith("-")
                    else [records["a"]["id"], *tied_dates, records["d"]["id"]])
    else:
        by_id = sorted(records.values(), key=lambda item: item["id"])
        expected = [item["id"] for item in sorted(by_id, key=lambda item: datetime.fromisoformat(item["created_at"]),
                                                   reverse=actual_sort.startswith("-"))]
    page = response.json()
    assert page["total"] == 4
    assert [item["id"] for item in page["items"]] == expected
    assert page["limit"] == 20
    assert page["offset"] == 0


@pytest.mark.parametrize("reader", ["owner", "admin"])
def test_booking_pages_have_no_missing_or_duplicate_records(base_url, user_access_token, admin_access_token, booking_catalog, reader):
    token, scope = reader_options(reader, booking_catalog, user_access_token, admin_access_token)
    records = booking_catalog["bookings"]
    expected = [records["a"]["id"], *sorted(records[key]["id"] for key in "bc"), records["d"]["id"]]

    for limit, offset in ((2, 0), (2, 2), (2, 4), (1, 0), (100, 0)):
        response = list_bookings(base_url, token, {**scope, "sort": "check_in", "limit": limit, "offset": offset})
        assert response.status_code == 200, response.text
        page = response.json()
        assert page["total"] == len(expected)
        assert page["limit"] == limit
        assert page["offset"] == offset
        assert [item["id"] for item in page["items"]] == expected[offset:offset + limit], (limit, offset)


def test_admin_lists_both_owners_with_hotel_filter(base_url, admin_access_token, booking_catalog):
    response = list_bookings(base_url, admin_access_token, {"hotel_id": booking_catalog["hotels"][0]["id"]})
    assert response.status_code == 200, response.text
    expected = [booking_catalog["bookings"][key] for key in "ab"] + [booking_catalog["other"]]
    assert response.json()["total"] == 3
    assert {item["id"] for item in response.json()["items"]} == {item["id"] for item in expected}


@pytest.mark.parametrize("target", ["self", "other", "unknown"])
def test_owner_cannot_filter_by_any_user_id(base_url, user_access_token, booking_catalog, target):
    user_id = {"self": booking_catalog["owner_id"], "other": booking_catalog["other"]["user_id"],
               "unknown": str(uuid4())}[target]
    response = list_bookings(base_url, user_access_token, {"user_id": user_id})
    assert_api_error(response, status=403, code="FORBIDDEN")
    own = list_bookings(base_url, user_access_token)
    assert own.status_code == 200, own.text
    assert own.json()["total"] == 4
    assert {item["id"] for item in own.json()["items"]} == {item["id"] for item in booking_catalog["bookings"].values()}


@pytest.mark.parametrize("params", [
    {"limit": 0}, {"limit": 101}, {"limit": "text"}, {"offset": -1},
    {"status": "unknown"}, {"hotel_id": "bad"}, {"user_id": "bad"},
    {"check_in_from": "not-a-date"}, {"check_in_to": "2030-02-30"},
])
def test_booking_list_rejects_invalid_query(base_url, admin_access_token, params):
    response = list_bookings(base_url, admin_access_token, params)
    body = assert_api_error(response, status=422, code="VALIDATION_ERROR")
    assert any(item["field"] == f"query.{next(iter(params))}" for item in body["error"]["details"])


@pytest.mark.parametrize("params,code", [
    ({"sort": "unknown"}, "INVALID_SORT"), ({"sort": "--check_in"}, "INVALID_SORT"),
    ({"check_in_from": "2030-01-03", "check_in_to": "2030-01-02"}, "INVALID_FILTER_RANGE"),
])
def test_booking_list_rejects_invalid_sort_and_range(base_url, user_access_token, params, code):
    response = list_bookings(base_url, user_access_token, params)
    assert_api_error(response, status=422, code=code)


@pytest.mark.parametrize("field", ["hotel_id", "user_id"])
def test_admin_filter_by_unknown_resource_is_empty(base_url, admin_access_token, field):
    response = list_bookings(base_url, admin_access_token, {field: str(uuid4())})
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 0
    assert response.json()["items"] == []
