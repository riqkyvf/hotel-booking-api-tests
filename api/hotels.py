import requests

from api.headers import authorization_headers


def list_hotels(base_url, params=None, access_token=None):
    headers = authorization_headers(access_token)
    return requests.get(
        f"{base_url}/hotels", params=params, headers=headers, timeout=10
    )


def get_hotel(base_url, hotel_id, access_token=None):
    headers = authorization_headers(access_token)
    return requests.get(
        f"{base_url}/hotels/{hotel_id}", headers=headers, timeout=10
    )


def create_hotel(base_url, access_token, data):
    return requests.post(
        f"{base_url}/hotels",
        json=data,
        headers=authorization_headers(access_token),
        timeout=10,
    )


def archive_hotel(base_url, access_token, hotel_id):
    return requests.delete(
        f"{base_url}/hotels/{hotel_id}",
        headers=authorization_headers(access_token),
        timeout=10,
    )
