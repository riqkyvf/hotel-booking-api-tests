from functools import partial
from uuid import uuid4

import pytest

from api.bookings import cancel_booking
from api.payments import create_payment, simulate_payment_failure, simulate_payment_success
from tests.assertions import assert_api_error


@pytest.mark.parametrize("operation, path_field", [
    pytest.param(cancel_booking, "booking_id", id="cancel_booking"),
    pytest.param(create_payment, "booking_id", id="create_payment"),
    pytest.param(simulate_payment_success, "payment_id", id="simulate_success"),
    pytest.param(partial(simulate_payment_failure, data={"reason": "Payment declined"}),
                 "payment_id", id="simulate_failure"),
])
@pytest.mark.parametrize("identifier, status, code", [
    pytest.param("not-a-uuid", 422, "VALIDATION_ERROR", id="malformed_uuid"),
    pytest.param(None, 404, "NOT_FOUND", id="unknown_uuid"),
])
def test_booking_and_payment_mutations_reject_invalid_ids(
    base_url, user_access_token, operation, path_field, identifier, status, code,
):
    resource_id = str(uuid4()) if identifier is None else identifier
    response = operation(base_url, user_access_token, resource_id)

    error = assert_api_error(response, status=status, code=code)["error"]
    if status == 422:
        assert any(detail["field"] == f"path.{path_field}" for detail in error["details"])
