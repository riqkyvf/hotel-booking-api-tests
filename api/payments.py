import requests

from api.headers import authorization_headers


def create_payment(base_url, access_token, booking_id):
    headers = authorization_headers(access_token)
    return requests.post(
        f"{base_url}/bookings/{booking_id}/payments", headers=headers, timeout=10
    )


def get_payment(base_url, access_token, payment_id):
    headers = authorization_headers(access_token)
    return requests.get(
        f"{base_url}/payments/{payment_id}", headers=headers, timeout=10
    )


def simulate_payment_success(base_url, access_token, payment_id):
    headers = authorization_headers(access_token)
    return requests.post(
        f"{base_url}/payments/{payment_id}/simulate-success", headers=headers, timeout=10
    )


def simulate_payment_failure(base_url, access_token, payment_id, data=None, *, raw_body=None):
    headers = authorization_headers(access_token)
    if raw_body is not None:
        headers["Content-Type"] = "application/json"
        return requests.post(
            f"{base_url}/payments/{payment_id}/simulate-failure",
            data=raw_body, headers=headers, timeout=10,
        )
    return requests.post(
        f"{base_url}/payments/{payment_id}/simulate-failure",
        json=data, headers=headers, timeout=10,
    )
