import base64

import pytest

from api.bookings import list_bookings
from api.hotels import create_hotel
from api.users import get_profile
from data.hotels import HOTEL_TEMPLATE
from tests.assertions import assert_api_error


@pytest.mark.parametrize("token_kind", [
    pytest.param("missing", marks=pytest.mark.smoke),
    "empty", "malformed", "invalid_signature",
])
@pytest.mark.parametrize("operation", ["profile", "bookings", "admin_create_hotel"])
def test_protected_operations_reject_invalid_credentials(
    base_url, user_access_token, token_kind, operation,
):
    token = {"missing": None, "empty": "", "malformed": "invalid-token"}.get(token_kind)
    if token_kind == "invalid_signature":
        header, payload, signature = user_access_token.split(".")
        # Change the first signature byte, keeping valid base64url and original claims.
        signature_bytes = bytearray(base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4)))
        signature_bytes[0] ^= 1
        damaged = base64.urlsafe_b64encode(signature_bytes).rstrip(b"=").decode()
        token = f"{header}.{payload}.{damaged}"

    if operation == "profile":
        response = get_profile(base_url, token)
    elif operation == "bookings":
        response = list_bookings(base_url, token)
    else:
        response = create_hotel(base_url, token, HOTEL_TEMPLATE.copy())

    assert_api_error(response, status=401, code="UNAUTHORIZED")
    assert response.headers.get("WWW-Authenticate") == "Bearer"
    if token:
        assert token not in response.text

    # Rejection must not disable the valid user's access.
    valid = get_profile(base_url, user_access_token)
    assert valid.status_code == 200, valid.text
