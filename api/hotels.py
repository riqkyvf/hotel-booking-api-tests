import requests


def list_hotels(base_url, params=None, access_token=None):
    headers = {}
    if access_token is not None:
        headers["Authorization"] = f"Bearer {access_token}"
    return requests.get(
        f"{base_url}/hotels", params=params, headers=headers, timeout=10
    )


def get_hotel(base_url, hotel_id, access_token=None):
    headers = {}
    if access_token is not None:
        headers["Authorization"] = f"Bearer {access_token}"
    return requests.get(
        f"{base_url}/hotels/{hotel_id}", headers=headers, timeout=10
    )


def create_hotel(base_url, access_token, data):
    return requests.post(
        f"{base_url}/hotels",
        json=data,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )


def archive_hotel(base_url, access_token, hotel_id):
    return requests.delete(
        f"{base_url}/hotels/{hotel_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
