from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from jsonschema import validate

from api.hotels import archive_hotel, create_hotel, get_hotel, list_hotels
from data.hotels import (
    HOTEL_CATALOG_CASES,
    HOTEL_CITY_VARIANTS,
    HOTEL_PAGINATION_CASES,
    HOTEL_RATING_CASES,
    HOTEL_READER_ROLES,
    HOTEL_SORT_CASES,
    HOTEL_TEMPLATE,
    HOTEL_UNSCOPED_RATING_CASES,
    INVALID_HOTEL_QUERY_CASES,
    INVALID_HOTEL_SORTS,
    INVALID_HOTEL_UUIDS,
)
from tests.assertions import assert_api_error
from schemas.hotel_response import HOTEL_PAGE_SCHEMA, HOTEL_SCHEMA


@pytest.fixture
def hotel_catalog(base_url, admin_access_token):
    city = f"QA_{uuid4().hex}"
    hotels = {}
    for key, case in HOTEL_CATALOG_CASES.items():
        payload = {**HOTEL_TEMPLATE, **case, "city": city}
        response = create_hotel(base_url, admin_access_token, payload)

        assert response.status_code == 201, response.text
        hotel = response.json()
        for field in ("name", "city", "address", "description"):
            assert hotel[field] == payload[field]
        assert Decimal(hotel["rating"]) == Decimal(payload["rating"])
        assert hotel["is_archived"] is False
        hotels[key] = hotel

    neighbor = create_hotel(
        base_url,
        admin_access_token,
        {**HOTEL_TEMPLATE, "city": city + " District", "name": "Neighbor Hotel"},
    )
    assert neighbor.status_code == 201, neighbor.text

    return {"city": city, "hotels": hotels, "neighbor": neighbor.json()}


@pytest.fixture
def hotel(base_url, admin_access_token):
    response = create_hotel(
        base_url,
        admin_access_token,
        {**HOTEL_TEMPLATE, "city": f"Details_{uuid4().hex}"},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def archived_hotel(base_url, admin_access_token, hotel):
    response = archive_hotel(base_url, admin_access_token, hotel["id"])
    assert response.status_code == 204, response.text
    return hotel


@pytest.fixture
def archived_catalog_hotel(base_url, admin_access_token, hotel_catalog):
    response = create_hotel(
        base_url,
        admin_access_token,
        {**HOTEL_TEMPLATE, "city": hotel_catalog["city"], "name": "Archived Hotel"},
    )
    assert response.status_code == 201, response.text
    hotel = response.json()

    archived = archive_hotel(base_url, admin_access_token, hotel["id"])
    assert archived.status_code == 204, archived.text
    return hotel


def test_hotels_default_pagination(base_url):
    response = list_hotels(base_url)

    assert response.status_code == 200, response.text
    body = response.json()
    validate(instance=body, schema=HOTEL_PAGE_SCHEMA)
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert len(body["items"]) == min(body["total"], 20)
    assert response.headers.get("X-Request-ID")
    for hotel in body["items"]:
        UUID(hotel["id"])
        assert Decimal("0") <= Decimal(hotel["rating"]) <= Decimal("5")
        assert hotel["is_archived"] is False


@pytest.mark.parametrize("limit,offset", HOTEL_PAGINATION_CASES)
def test_hotels_pagination(base_url, hotel_catalog, limit, offset):
    hotels = hotel_catalog["hotels"]
    expected = sorted([hotels["alpha_one"]["id"], hotels["alpha_two"]["id"]])
    expected += [hotels["beta"]["id"], hotels["omega"]["id"]]

    response = list_hotels(
        base_url,
        {"city": hotel_catalog["city"], "limit": limit, "offset": offset, "sort": "name"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    validate(instance=body, schema=HOTEL_PAGE_SCHEMA)
    assert body["total"] == 4
    assert body["limit"] == limit
    assert body["offset"] == offset
    assert [hotel["id"] for hotel in body["items"]] == expected[offset:offset + limit]


def test_hotels_pagination_pages(base_url, hotel_catalog):
    pages = []
    for offset in (0, 2):
        response = list_hotels(
            base_url,
            {"city": hotel_catalog["city"], "limit": 2, "offset": offset, "sort": "name"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 4
        assert body["limit"] == 2
        assert body["offset"] == offset
        pages.append([hotel["id"] for hotel in body["items"]])

    hotels = hotel_catalog["hotels"]
    expected = sorted([hotels["alpha_one"]["id"], hotels["alpha_two"]["id"]])
    expected += [hotels["beta"]["id"], hotels["omega"]["id"]]
    assert pages[0] + pages[1] == expected
    assert set(pages[0]).isdisjoint(pages[1])


def test_hotels_unknown_city(base_url):
    response = list_hotels(base_url, {"city": f"no_match_{uuid4().hex}"})

    assert response.status_code == 200, response.text
    body = response.json()
    validate(instance=body, schema=HOTEL_PAGE_SCHEMA)
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.parametrize("variant", HOTEL_CITY_VARIANTS)
def test_hotels_city_normalization(base_url, hotel_catalog, variant):
    city = hotel_catalog["city"]
    if variant == "lowercase":
        city = city.lower()
    elif variant == "uppercase":
        city = city.upper()
    elif variant == "leading_spaces":
        city = "  " + city
    elif variant == "trailing_spaces":
        city += "  "
    elif variant == "both":
        city = f"  {city.upper()}  "

    response = list_hotels(base_url, {"city": city, "limit": 100})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 4
    assert len(body["items"]) == 4
    assert {hotel["id"] for hotel in body["items"]} == {
        hotel["id"] for hotel in hotel_catalog["hotels"].values()
    }
    assert all(hotel["city"] == hotel_catalog["city"] for hotel in body["items"])
    assert hotel_catalog["neighbor"]["id"] not in {hotel["id"] for hotel in body["items"]}


def test_hotels_city_requires_full_match(base_url, hotel_catalog):
    response = list_hotels(base_url, {"city": hotel_catalog["city"][:-1]})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.parametrize("params,low,high,minimum_total", HOTEL_UNSCOPED_RATING_CASES)
def test_hotels_rating_without_city(
    base_url, hotel_catalog, params, low, high, minimum_total
):
    response = list_hotels(base_url, {**params, "limit": 100})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] >= minimum_total
    assert body["items"]
    assert all(
        Decimal(low) <= Decimal(hotel["rating"]) <= Decimal(high)
        for hotel in body["items"]
    )
    assert all(hotel["is_archived"] is False for hotel in body["items"])


@pytest.mark.parametrize("params,expected_keys", HOTEL_RATING_CASES)
def test_hotels_rating_filter(base_url, hotel_catalog, params, expected_keys):
    response = list_hotels(
        base_url, {**params, "city": hotel_catalog["city"], "limit": 100}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == len(expected_keys)
    assert len(body["items"]) == len(expected_keys)
    assert {hotel["id"] for hotel in body["items"]} == {
        hotel_catalog["hotels"][key]["id"] for key in expected_keys
    }
    assert all(hotel["city"] == hotel_catalog["city"] for hotel in body["items"])


@pytest.mark.parametrize("sort,expected_names", HOTEL_SORT_CASES)
def test_hotels_sorting(base_url, hotel_catalog, sort, expected_names):
    params = {"city": hotel_catalog["city"], "limit": 100}
    if sort is not None:
        params["sort"] = sort

    response = list_hotels(base_url, params)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 4
    hotels = hotel_catalog["hotels"]
    assert [hotel["name"] for hotel in body["items"]] == list(expected_names)
    assert {hotel["id"] for hotel in body["items"]} == {
        hotel["id"] for hotel in hotels.values()
    }
    expected_by_id = {hotel["id"]: hotel for hotel in hotels.values()}
    for hotel in body["items"]:
        expected_hotel = expected_by_id[hotel["id"]]
        assert hotel["name"] == expected_hotel["name"]
        assert hotel["rating"] == expected_hotel["rating"]

    # The two Alpha hotels have equal names and ratings in all sort variants.
    expected_alpha_ids = sorted([hotels["alpha_one"]["id"], hotels["alpha_two"]["id"]])
    actual_alpha_ids = [
        hotel["id"] for hotel in body["items"] if hotel["name"] == "Alpha Hotel"
    ]
    assert actual_alpha_ids == expected_alpha_ids


@pytest.mark.parametrize("role", HOTEL_READER_ROLES)
@pytest.mark.parametrize("include_archived", [None, False], ids=["omitted", "false"])
def test_hotels_hide_archived_by_default(
    base_url, hotel_catalog, archived_catalog_hotel, user_access_token, admin_access_token,
    role, include_archived,
):
    token = {"guest": None, "user": user_access_token, "admin": admin_access_token}[role]
    params = {"city": hotel_catalog["city"], "limit": 100}
    if include_archived is not None:
        params["include_archived"] = include_archived

    response = list_hotels(base_url, params, access_token=token)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 4
    assert len(body["items"]) == 4
    assert {hotel["id"] for hotel in body["items"]} == {
        hotel["id"] for hotel in hotel_catalog["hotels"].values()
    }
    assert all(hotel["is_archived"] is False for hotel in body["items"])
    assert archived_catalog_hotel["id"] not in {hotel["id"] for hotel in body["items"]}


def test_hotels_admin_can_include_archived(
    base_url, hotel_catalog, archived_catalog_hotel, admin_access_token
):
    response = list_hotels(
        base_url,
        {"city": hotel_catalog["city"], "include_archived": True, "limit": 100},
        access_token=admin_access_token,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    validate(instance=body, schema=HOTEL_PAGE_SCHEMA)
    assert body["total"] == 5
    assert len(body["items"]) == 5
    assert {hotel["id"] for hotel in body["items"]} == {
        hotel["id"] for hotel in hotel_catalog["hotels"].values()
    } | {archived_catalog_hotel["id"]}
    assert [hotel["id"] for hotel in body["items"] if hotel["is_archived"]] == [
        archived_catalog_hotel["id"]
    ]


@pytest.mark.parametrize("role", ["guest", "user"])
def test_hotels_archived_list_requires_admin(base_url, user_access_token, role):
    token = None if role == "guest" else user_access_token
    response = list_hotels(base_url, {"include_archived": True}, access_token=token)

    assert_api_error(response, status=403, code="FORBIDDEN")


@pytest.mark.parametrize("field,value", INVALID_HOTEL_QUERY_CASES)
def test_hotels_invalid_query_parameters(base_url, field, value):
    response = list_hotels(base_url, {field: value})

    body = assert_api_error(response, status=422, code="VALIDATION_ERROR")
    assert any(detail["field"] == f"query.{field}" for detail in body["error"]["details"])


def test_hotels_invalid_rating_range(base_url):
    response = list_hotels(base_url, {"min_rating": "4", "max_rating": "3"})

    assert_api_error(response, status=422, code="INVALID_FILTER_RANGE")


@pytest.mark.parametrize("sort", INVALID_HOTEL_SORTS)
def test_hotels_invalid_sort(base_url, sort):
    response = list_hotels(base_url, {"sort": sort})

    assert_api_error(response, status=422, code="INVALID_SORT")


@pytest.mark.parametrize("role", HOTEL_READER_ROLES)
def test_get_hotel_for_each_role(
    base_url, hotel, user_access_token, admin_access_token, role
):
    expected = hotel
    token = {"guest": None, "user": user_access_token, "admin": admin_access_token}[role]
    response = get_hotel(base_url, expected["id"], access_token=token)

    assert response.status_code == 200, response.text
    body = response.json()
    validate(instance=body, schema=HOTEL_SCHEMA)
    assert body == expected
    assert body["is_archived"] is False
    assert response.headers.get("X-Request-ID")


def test_get_hotel_not_found(base_url):
    response = get_hotel(base_url, str(uuid4()))

    assert_api_error(response, status=404, code="NOT_FOUND")


@pytest.mark.parametrize("hotel_id", INVALID_HOTEL_UUIDS)
def test_get_hotel_invalid_uuid(base_url, hotel_id):
    response = get_hotel(base_url, hotel_id)

    body = assert_api_error(response, status=422, code="VALIDATION_ERROR")
    assert any(detail["field"] == "path.hotel_id" for detail in body["error"]["details"])


@pytest.mark.parametrize("role", ["guest", "user"])
def test_get_archived_hotel_hidden(base_url, archived_hotel, user_access_token, role):
    token = None if role == "guest" else user_access_token
    response = get_hotel(base_url, archived_hotel["id"], access_token=token)

    assert_api_error(response, status=404, code="NOT_FOUND")


def test_get_archived_hotel_as_admin(base_url, archived_hotel, admin_access_token):
    response = get_hotel(base_url, archived_hotel["id"], access_token=admin_access_token)

    assert response.status_code == 200, response.text
    hotel = response.json()
    validate(instance=hotel, schema=HOTEL_SCHEMA)
    assert hotel["is_archived"] is True
    for field in ("id", "name", "city", "address", "description", "rating", "created_at"):
        assert hotel[field] == archived_hotel[field]
    assert response.headers.get("X-Request-ID")
