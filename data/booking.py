import pytest


BOOKING_ROOM_DATA = {
    "room_number": "101",
    "type": "double",
    "capacity": 2,
    "price_per_night": "1234.56",
}

BOOKING_NIGHTS = 3
BOOKING_GUESTS = 2
BOOKING_CHECK_IN_OFFSET_DAYS = 2

# Offsets in days from the first booking's check-in; its stay is three nights.
OVERLAPPING_STAYS = (
    pytest.param(0, 3, id="same_dates"),
    pytest.param(-1, 1, id="overlap_left"),
    pytest.param(2, 4, id="overlap_right"),
    pytest.param(1, 2, id="inside_existing"),
    pytest.param(-1, 4, id="contains_existing"),
)

ADJACENT_STAYS = (
    pytest.param(-1, 0, id="ends_at_existing_check_in"),
    pytest.param(3, 4, id="starts_at_existing_check_out"),
)

BLOCKING_BOOKING_STATUSES = ("pending_payment", "confirmed")

CANCELLATION_PAYMENT_CASES = (
    pytest.param(None, None, id="without_payment"),
    pytest.param("pending", "cancelled", id="pending_payment"),
    pytest.param("succeeded", "refunded", id="paid_booking"),
)

INVALID_CHECK_OUT_OFFSETS = (
    pytest.param(0, id="same_day"),
    pytest.param(-1, id="before_check_in"),
)

VALID_STAY_BOUNDARIES = (
    pytest.param(0, BOOKING_NIGHTS, id="check_in_today"),
    pytest.param(BOOKING_CHECK_IN_OFFSET_DAYS, 1, id="one_night"),
    pytest.param(BOOKING_CHECK_IN_OFFSET_DAYS, 14, id="fourteen_nights"),
)
