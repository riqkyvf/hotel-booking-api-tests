from decimal import Decimal
from uuid import uuid4

import pytest
from jsonschema import validate

from api.hotels import create_hotel, list_hotels
from api.rooms import archive_room, create_room, update_room_availability
from data.hotel_prices import (
    HOTEL_FILTERED_PRICE_SORT_CASES,
    HOTEL_PRICE_AND_RATING_CASES,
    HOTEL_PRICE_FILTER_CASES,
    HOTEL_PRICE_SORT_CASES,
    INVALID_HOTEL_PRICE_CASES,
    PRICE_HOTELS,
    PRICE_NEIGHBOR_HOTEL,
    PRICE_SORT_DIRECTIONS,
    ROOM_TEMPLATE,
)
from data.hotels import HOTEL_TEMPLATE
from tests.assertions import assert_api_error
from schemas.hotel_response import HOTEL_PAGE_SCHEMA


def create_priced_hotel(base_url, access_token, city, case):
    """Create one hotel with rooms and verify that setup succeeded."""
    for _, state in case["rooms"]:
        assert state in {"active", "disabled", "archived"}, f"Unknown room state: {state!r}"

    response = create_hotel(
        base_url,
        access_token,
        {**HOTEL_TEMPLATE, "name": case["name"], "rating": case["rating"], "city": city},
    )
    assert response.status_code == 201, response.text
    hotel = response.json()
    assert hotel["city"] == city
    assert Decimal(hotel["rating"]) == Decimal(case["rating"])

    for number, (price, state) in enumerate(case["rooms"], start=1):
        created = create_room(
            base_url,
            access_token,
            hotel["id"],
            {**ROOM_TEMPLATE, "room_number": str(number), "price_per_night": price},
        )
        assert created.status_code == 201, created.text
        room = created.json()
        assert room["hotel_id"] == hotel["id"]
        assert Decimal(room["price_per_night"]) == Decimal(price)
        assert room["is_available"] is True
        assert room["is_archived"] is False

        if state == "disabled":
            disabled = update_room_availability(
                base_url, access_token, room["id"], {"is_available": False}
            )
            assert disabled.status_code == 200, disabled.text
            disabled_room = disabled.json()
            assert disabled_room["id"] == room["id"]
            assert disabled_room["is_available"] is False
        elif state == "archived":
            archived = archive_room(base_url, access_token, room["id"])
            assert archived.status_code == 204, archived.text

    return hotel


@pytest.fixture
def price_filter_catalog(base_url, admin_access_token):
    city = f"PriceFilter_{uuid4().hex}"
    hotels = {}
    for key, case in PRICE_HOTELS.items():
        hotels[key] = create_priced_hotel(base_url, admin_access_token, city, case)
    return {"city": city, "hotels": hotels}


@pytest.fixture
def price_comparison_catalog(base_url, admin_access_token):
    city = f"PriceCompare_{uuid4().hex}"
    hotels = {}
    for key in ("mixed", "midrange"):
        hotels[key] = create_priced_hotel(base_url, admin_access_token, city, PRICE_HOTELS[key])
    neighbor = create_priced_hotel(
        base_url, admin_access_token, city + " Other", PRICE_NEIGHBOR_HOTEL
    )
    return {"city": city, "hotels": hotels, "neighbor": neighbor}


@pytest.fixture
def price_sort_catalog(base_url, admin_access_token):
    city = f"PriceSort_{uuid4().hex}"
    hotels = {}
    for key in ("midrange", "expensive", "five_digits"):
        hotels[key] = create_priced_hotel(base_url, admin_access_token, city, PRICE_HOTELS[key])
    return {"city": city, "hotels": hotels}


@pytest.fixture
def hotels_without_price(base_url, admin_access_token):
    city = f"NoPrice_{uuid4().hex}"
    hotels = {}
    for key in ("midrange", "disabled_only", "archived_only", "empty"):
        hotels[key] = create_priced_hotel(base_url, admin_access_token, city, PRICE_HOTELS[key])
    return {"city": city, "hotels": hotels}


@pytest.fixture
def price_pagination_catalog(base_url, admin_access_token):
    city = f"PricePage_{uuid4().hex}"
    hotels = {}
    for key in ("mixed", "tied", "midrange", "expensive", "empty"):
        hotels[key] = create_priced_hotel(base_url, admin_access_token, city, PRICE_HOTELS[key])
    return {"city": city, "hotels": hotels}


@pytest.mark.parametrize("params,expected_keys", HOTEL_PRICE_FILTER_CASES)
def test_hotels_price_filter(base_url, price_filter_catalog, params, expected_keys):
    response = list_hotels(
        base_url, {**params, "city": price_filter_catalog["city"], "limit": 100}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    validate(instance=body, schema=HOTEL_PAGE_SCHEMA)
    assert body["total"] == len(expected_keys)
    assert len(body["items"]) == len(expected_keys)
    assert {hotel["id"] for hotel in body["items"]} == {
        price_filter_catalog["hotels"][key]["id"] for key in expected_keys
    }


@pytest.mark.parametrize("sort,expected_keys", HOTEL_PRICE_SORT_CASES)
def test_hotels_price_sorting(base_url, price_sort_catalog, sort, expected_keys):
    response = list_hotels(
        base_url, {"city": price_sort_catalog["city"], "limit": 100, "sort": sort}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    validate(instance=body, schema=HOTEL_PAGE_SCHEMA)
    assert body["total"] == 3
    expected_ids = [price_sort_catalog["hotels"][key]["id"] for key in expected_keys]
    actual_ids = [hotel["id"] for hotel in body["items"]]
    assert actual_ids == expected_ids


@pytest.mark.parametrize("sort,keys", HOTEL_FILTERED_PRICE_SORT_CASES)
def test_hotels_filtered_price_sorting(base_url, price_comparison_catalog, sort, keys):
    response = list_hotels(
        base_url,
        {"city": price_comparison_catalog["city"], "min_price": "6000", "max_price": "8000",
         "sort": sort, "limit": 100},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 2
    assert [hotel["id"] for hotel in body["items"]] == [
        price_comparison_catalog["hotels"][key]["id"] for key in keys
    ]


@pytest.mark.parametrize("rating_params,keys", HOTEL_PRICE_AND_RATING_CASES)
def test_hotels_price_and_rating_filter(base_url, price_comparison_catalog, rating_params, keys):
    response = list_hotels(
        base_url,
        {**rating_params, "city": price_comparison_catalog["city"], "min_price": "6000",
         "max_price": "8000", "limit": 100},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == len(keys)
    assert len(body["items"]) == len(keys)
    assert {hotel["id"] for hotel in body["items"]} == {
        price_comparison_catalog["hotels"][key]["id"] for key in keys
    }
    assert all(hotel["city"] == price_comparison_catalog["city"] for hotel in body["items"])
    assert price_comparison_catalog["neighbor"]["id"] not in {hotel["id"] for hotel in body["items"]}


@pytest.mark.parametrize("sort", PRICE_SORT_DIRECTIONS)
def test_hotels_price_pagination(base_url, price_pagination_catalog, sort):
    hotels = price_pagination_catalog["hotels"]
    tied_ids = sorted([hotels["mixed"]["id"], hotels["tied"]["id"]])
    if sort == "price":
        expected_ids = tied_ids + [
            hotels["midrange"]["id"], hotels["expensive"]["id"], hotels["empty"]["id"],
        ]
    else:
        expected_ids = [hotels["expensive"]["id"], hotels["midrange"]["id"]]
        expected_ids += tied_ids + [hotels["empty"]["id"]]

    collected_ids = []
    for offset in (0, 2, 4):
        response = list_hotels(
            base_url,
            {"city": price_pagination_catalog["city"], "sort": sort,
             "limit": 2, "offset": offset},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 5
        assert body["limit"] == 2
        assert body["offset"] == offset
        page_ids = [hotel["id"] for hotel in body["items"]]
        assert page_ids == expected_ids[offset:offset + 2]
        collected_ids.extend(page_ids)

    assert collected_ids == expected_ids
    assert len(collected_ids) == len(set(collected_ids)) == 5


@pytest.mark.parametrize("field,value", INVALID_HOTEL_PRICE_CASES)
def test_hotels_invalid_price_parameters(base_url, field, value):
    response = list_hotels(base_url, {field: value})

    body = assert_api_error(response, status=422, code="VALIDATION_ERROR")
    assert any(detail["field"] == f"query.{field}" for detail in body["error"]["details"])


def test_hotels_invalid_price_range(base_url):
    response = list_hotels(base_url, {"min_price": "9000", "max_price": "1000"})

    assert_api_error(response, status=422, code="INVALID_FILTER_RANGE")


@pytest.mark.parametrize("sort", PRICE_SORT_DIRECTIONS)
def test_hotels_without_price_are_last(base_url, hotels_without_price, sort):
    response = list_hotels(
        base_url, {"city": hotels_without_price["city"], "sort": sort, "limit": 100}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    validate(instance=body, schema=HOTEL_PAGE_SCHEMA)
    assert body["total"] == 4

    hotels = hotels_without_price["hotels"]
    without_price_ids = sorted([
        hotels["disabled_only"]["id"], hotels["archived_only"]["id"], hotels["empty"]["id"],
    ])
    expected_ids = [hotels["midrange"]["id"]] + without_price_ids
    actual_ids = [hotel["id"] for hotel in body["items"]]
    assert actual_ids == expected_ids
