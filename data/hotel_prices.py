import pytest


ROOM_TEMPLATE = {
    "room_number": "1",
    "type": "double",
    "capacity": 2,
    "price_per_night": "3000.00",
}

# Room entries are (price, state); only active rooms contribute to price.
PRICE_HOTELS = {
    "mixed": {
        "name": "A Mixed",
        "rating": "4.0",
        "rooms": (
            ("1000.00", "active"),
            ("7000.00", "active"),
        ),
    },
    "midrange": {
        "name": "B Midrange",
        "rating": "3.0",
        "rooms": (
            ("6500.00", "active"),
        ),
    },
    "tied": {
        "name": "C Tied",
        "rating": "5.0",
        "rooms": (
            ("1000.00", "active"),
        ),
    },
    "expensive": {
        "name": "D Expensive",
        "rating": "2.0",
        "rooms": (
            ("9000.00", "active"),
            ("500.00", "disabled"),
            ("100.00", "archived"),
        ),
    },
    "disabled_only": {
        "name": "E Disabled",
        "rating": "4.0",
        "rooms": (
            ("600.00", "disabled"),
        ),
    },
    "archived_only": {
        "name": "F Archived Room",
        "rating": "4.0",
        "rooms": (
            ("400.00", "archived"),
        ),
    },
    "empty": {
        "name": "G No Rooms",
        "rating": "4.0",
        "rooms": (),
    },
    "boundary": {
        "name": "H Boundaries",
        "rating": "1.0",
        "rooms": (
            ("0.01", "active"),
            ("9999999999.99", "active"),
        ),
    },
    "five_digits": {
        "name": "I Five Digits",
        "rating": "2.5",
        "rooms": (
            ("10000.00", "active"),
        ),
    },
}

# Expected keys are explicit so tests do not reproduce the server's filtering logic.
HOTEL_PRICE_FILTER_CASES = (
    pytest.param({"min_price": "0"},
                 ("mixed", "midrange", "tied", "expensive", "boundary", "five_digits"),
                 id="minimum_zero"),
    pytest.param({"max_price": "0"}, (), id="maximum_zero"),
    pytest.param({"min_price": "0.01", "max_price": "0.01"}, ("boundary",),
                 id="minimum_room_price_inclusive"),
    pytest.param({"min_price": "9999999999.99", "max_price": "9999999999.99"},
                 ("boundary",), id="maximum_room_price_inclusive"),
    pytest.param({"max_price": "1000"}, ("mixed", "tied", "boundary"),
                 id="maximum_only"),
    pytest.param({"min_price": "6500"},
                 ("mixed", "midrange", "expensive", "boundary", "five_digits"),
                 id="minimum_only"),
    pytest.param({"max_price": "6500"}, ("mixed", "midrange", "tied", "boundary"),
                 id="maximum_inclusive"),
    pytest.param({"min_price": "1000", "max_price": "6500"},
                 ("mixed", "midrange", "tied"), id="range_inclusive"),
    pytest.param({"min_price": "1000", "max_price": "1000"},
                 ("mixed", "tied"), id="equal_prices"),
    pytest.param({"min_price": "6000", "max_price": "8000"},
                 ("mixed", "midrange"), id="matching_room_not_minimum"),
    pytest.param({"min_price": "3000", "max_price": "5000"}, (),
                 id="both_bounds_must_match_one_room"),
    pytest.param({"min_price": "400", "max_price": "600"}, (),
                 id="disabled_and_archived_do_not_match"),
    pytest.param({"min_price": "9000", "max_price": "9000"}, ("expensive",),
                 id="active_expensive_room"),
    pytest.param({"min_price": "10000", "max_price": "10000"}, ("five_digits",),
                 id="five_digit_price"),
    pytest.param({"min_price": "6999.99", "max_price": "7000.00"}, ("mixed",),
                 id="fractional_boundary"),
)

HOTEL_PRICE_SORT_CASES = (
    pytest.param("price", ("midrange", "expensive", "five_digits"), id="ascending"),
    pytest.param("-price", ("five_digits", "expensive", "midrange"), id="descending"),
)

PRICE_SORT_DIRECTIONS = (
    pytest.param("price", id="ascending"),
    pytest.param("-price", id="descending"),
)

PRICE_NEIGHBOR_HOTEL = {
    "name": "Neighbor Price Hotel",
    "rating": "4.0",
    "rooms": (("6500.00", "active"),),
}

HOTEL_FILTERED_PRICE_SORT_CASES = (
    pytest.param("price", ("mixed", "midrange"), id="ascending"),
    pytest.param("-price", ("midrange", "mixed"), id="descending"),
)

HOTEL_PRICE_AND_RATING_CASES = (
    pytest.param({"min_rating": "4"}, ("mixed",), id="minimum_rating"),
    pytest.param({"max_rating": "3"}, ("midrange",), id="maximum_rating"),
)

INVALID_HOTEL_PRICE_CASES = (
    pytest.param("min_price", "-0.01", id="negative_minimum"),
    pytest.param("max_price", "-0.01", id="negative_maximum"),
    pytest.param("min_price", "10000000000", id="large_minimum"),
    pytest.param("max_price", "10000000000", id="large_maximum"),
    pytest.param("min_price", "text", id="nonnumeric_minimum"),
    pytest.param("max_price", "text", id="nonnumeric_maximum"),
)
