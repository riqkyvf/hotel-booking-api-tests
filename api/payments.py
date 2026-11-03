import requests


def create_payment(base_url, access_token, booking_id):
    headers = {}
    if access_token is not None:
        headers["Authorization"] = f"Bearer {access_token}"
    return requests.post(
        f"{base_url}/bookings/{booking_id}/payments", headers=headers, timeout=10
    )


def get_payment(base_url, access_token, payment_id):
    headers = {}
    if access_token is not None:
        headers["Authorization"] = f"Bearer {access_token}"
    return requests.get(
        f"{base_url}/payments/{payment_id}", headers=headers, timeout=10
    )


def simulate_payment_success(base_url, access_token, payment_id):
    headers = {}
    if access_token is not None:
        headers["Authorization"] = f"Bearer {access_token}"
    return requests.post(
        f"{base_url}/payments/{payment_id}/simulate-success", headers=headers, timeout=10
    )
