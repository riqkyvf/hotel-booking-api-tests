import requests


def create_booking(base_url, access_token, data, idempotency_key):
    headers = {}
    if access_token is not None:
        headers["Authorization"] = f"Bearer {access_token}"
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    return requests.post(
        f"{base_url}/bookings", json=data, headers=headers, timeout=10
    )


def get_booking(base_url, access_token, booking_id):
    headers = {}
    if access_token is not None:
        headers["Authorization"] = f"Bearer {access_token}"
    return requests.get(
        f"{base_url}/bookings/{booking_id}", headers=headers, timeout=10
    )


def list_bookings(base_url, access_token, params=None):
    headers = {}
    if access_token is not None:
        headers["Authorization"] = f"Bearer {access_token}"
    return requests.get(
        f"{base_url}/bookings", params=params, headers=headers, timeout=10
    )
