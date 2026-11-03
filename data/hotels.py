import pytest


HOTEL_TEMPLATE = {
    "name": "QA Hotel",
    "city": "QA City",
    "address": "10 Test Street",
    "description": "Hotel for catalog tests",
    "rating": "3.0",
}

HOTEL_CATALOG_CASES = {
    "beta": {"name": "Beta Hotel", "rating": "0.0"},
    "alpha_one": {"name": "Alpha Hotel", "rating": "3.0"},
    "alpha_two": {"name": "Alpha Hotel", "rating": "3.0"},
    "omega": {"name": "Omega Hotel", "rating": "5.0"},
}

HOTEL_READER_ROLES = ("guest", "user", "admin")

HOTEL_CITY_VARIANTS = (
    "original", "lowercase", "uppercase", "leading_spaces", "trailing_spaces", "both"
)

HOTEL_PAGINATION_CASES = (
    pytest.param(1, 0, id="first_one"),
    pytest.param(1, 1, id="second_one"),
    pytest.param(2, 0, id="first_page"),
    pytest.param(2, 2, id="second_page"),
    pytest.param(100, 0, id="maximum_limit"),
    pytest.param(2, 4, id="offset_equals_total"),
    pytest.param(2, 10, id="offset_beyond_total"),
)

HOTEL_RATING_CASES = (
    pytest.param({"min_rating": "0"}, ("beta", "alpha_one", "alpha_two", "omega"),
                 id="minimum_boundary"),
    pytest.param({"max_rating": "5"}, ("beta", "alpha_one", "alpha_two", "omega"),
                 id="maximum_boundary"),
    pytest.param({"min_rating": "3"}, ("alpha_one", "alpha_two", "omega"),
                 id="minimum_inclusive"),
    pytest.param({"max_rating": "3"}, ("beta", "alpha_one", "alpha_two"),
                 id="maximum_inclusive"),
    pytest.param({"min_rating": "3", "max_rating": "3"}, ("alpha_one", "alpha_two"),
                 id="equal_bounds"),
    pytest.param({"min_rating": "0", "max_rating": "0"}, ("beta",), id="zero_only"),
    pytest.param({"min_rating": "5", "max_rating": "5"}, ("omega",), id="five_only"),
    pytest.param({"min_rating": "1", "max_rating": "4"}, ("alpha_one", "alpha_two"),
                 id="middle_range"),
    pytest.param({"min_rating": "4", "max_rating": "4"}, (), id="no_matches"),
)

HOTEL_UNSCOPED_RATING_CASES = (
    pytest.param({"min_rating": "3"}, "3", "5", 3, id="minimum_only"),
    pytest.param({"max_rating": "3"}, "0", "3", 3, id="maximum_only"),
)

HOTEL_SORT_CASES = (
    pytest.param(None, ("Alpha Hotel", "Alpha Hotel", "Beta Hotel", "Omega Hotel"),
                 id="default_name"),
    pytest.param("name", ("Alpha Hotel", "Alpha Hotel", "Beta Hotel", "Omega Hotel"),
                 id="name_ascending"),
    pytest.param("-name", ("Omega Hotel", "Beta Hotel", "Alpha Hotel", "Alpha Hotel"),
                 id="name_descending"),
    pytest.param("rating", ("Beta Hotel", "Alpha Hotel", "Alpha Hotel", "Omega Hotel"),
                 id="rating_ascending"),
    pytest.param("-rating", ("Omega Hotel", "Alpha Hotel", "Alpha Hotel", "Beta Hotel"),
                 id="rating_descending"),
)

INVALID_HOTEL_QUERY_CASES = (
    pytest.param("limit", 0, id="zero_limit"),
    pytest.param("limit", -1, id="negative_limit"),
    pytest.param("limit", 101, id="large_limit"),
    pytest.param("limit", "1.5", id="fractional_limit"),
    pytest.param("limit", "text", id="nonnumeric_limit"),
    pytest.param("offset", -1, id="negative_offset"),
    pytest.param("offset", "1.5", id="fractional_offset"),
    pytest.param("offset", "text", id="nonnumeric_offset"),
    pytest.param("min_rating", "-0.1", id="negative_min_rating"),
    pytest.param("min_rating", "5.1", id="large_min_rating"),
    pytest.param("min_rating", "text", id="nonnumeric_min_rating"),
    pytest.param("max_rating", "-0.1", id="negative_max_rating"),
    pytest.param("max_rating", "5.1", id="large_max_rating"),
    pytest.param("max_rating", "text", id="nonnumeric_max_rating"),
    pytest.param("include_archived", "not-a-boolean", id="invalid_archived_flag"),
)

INVALID_HOTEL_SORTS = ("unknown", "-unknown", "--name", "")

INVALID_HOTEL_UUIDS = (
    pytest.param("not-a-uuid", id="text"),
    pytest.param("123", id="number"),
    pytest.param("00000000-0000-0000-0000-00000000000z", id="invalid_hex"),
)
