import requests

from api.headers import authorization_headers


def create_booking(base_url, access_token, data=None, idempotency_key=None, *, raw_body=None):
    headers = authorization_headers(access_token)
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    if raw_body is not None:
        headers["Content-Type"] = "application/json"
        return requests.post(
            f"{base_url}/bookings", data=raw_body, headers=headers, timeout=10
        )
    return requests.post(
        f"{base_url}/bookings", json=data, headers=headers, timeout=10
    )


def get_booking(base_url, access_token, booking_id):
    headers = authorization_headers(access_token)
    return requests.get(
        f"{base_url}/bookings/{booking_id}", headers=headers, timeout=10
    )


def list_bookings(base_url, access_token, params=None):
    headers = authorization_headers(access_token)
    return requests.get(
        f"{base_url}/bookings", params=params, headers=headers, timeout=10
    )


def cancel_booking(base_url, access_token, booking_id):
    headers = authorization_headers(access_token)
    return requests.patch(
        f"{base_url}/bookings/{booking_id}/cancel", headers=headers, timeout=10
    )
