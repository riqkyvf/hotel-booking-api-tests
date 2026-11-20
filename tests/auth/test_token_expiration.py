import os
from datetime import datetime, timedelta, timezone

import allure
import jwt
import pytest

from api.users import get_profile
from tests.assertions import assert_api_error


@pytest.fixture
def jwt_test_secret():
    secret = os.getenv("JWT_SECRET")
    if secret:
        return secret

    message = "Set JWT_SECRET to the signing key of the dedicated test API"
    if os.getenv("GITHUB_ACTIONS") == "true":
        pytest.fail(message, pytrace=False)
    pytest.skip(message)


@pytest.mark.full
@allure.title("Истёкший JWT отклоняется, а действующий открывает профиль")
def test_profile_rejects_expired_token(base_url, jwt_test_secret, registered_user):
    user_id = registered_user["user"]["id"]
    now = datetime.now(timezone.utc)
    claims = {
        "sub": user_id,
        "iat": now - timedelta(minutes=65),
        "iss": "hotel-api",
        "aud": "hotel-api",
    }
    valid_token = jwt.encode(
        {**claims, "exp": now + timedelta(minutes=5)}, jwt_test_secret, algorithm="HS256",
    )
    expired_token = jwt.encode(
        {**claims, "exp": now - timedelta(minutes=5)}, jwt_test_secret, algorithm="HS256",
    )

    accepted = get_profile(base_url, valid_token)
    assert accepted.status_code == 200, "The test API must accept the matching JWT with a future expiration"
    assert accepted.json()["id"] == user_id

    rejected = get_profile(base_url, expired_token)
    assert_api_error(rejected, status=401, code="UNAUTHORIZED")
    assert rejected.headers.get("WWW-Authenticate") == "Bearer"
