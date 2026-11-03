import requests

from api.headers import authorization_headers


def list_rooms(base_url, hotel_id, params=None, access_token=None):
    return requests.get(
        f"{base_url}/hotels/{hotel_id}/rooms", params=params,
        headers=authorization_headers(access_token), timeout=10
    )


def get_room(base_url, room_id, access_token=None):
    return requests.get(
        f"{base_url}/rooms/{room_id}",
        headers=authorization_headers(access_token), timeout=10,
    )


def get_room_availability(base_url, room_id, params):
    return requests.get(
        f"{base_url}/rooms/{room_id}/availability", params=params, timeout=10
    )


def create_room(base_url, access_token, hotel_id, data):
    return requests.post(
        f"{base_url}/hotels/{hotel_id}/rooms",
        json=data,
        headers=authorization_headers(access_token),
        timeout=10,
    )


def update_room(base_url, access_token, room_id, data=None, *, raw_body=None):
    if raw_body is not None:
        return requests.put(
            f"{base_url}/rooms/{room_id}", data=raw_body,
            headers={**authorization_headers(access_token), "Content-Type": "application/json"},
            timeout=10,
        )
    return requests.put(
        f"{base_url}/rooms/{room_id}",
        json=data,
        headers=authorization_headers(access_token),
        timeout=10,
    )


def update_room_availability(base_url, access_token, room_id, data=None, *, raw_body=None):
    if raw_body is not None:
        return requests.patch(
            f"{base_url}/rooms/{room_id}/availability", data=raw_body,
            headers={**authorization_headers(access_token), "Content-Type": "application/json"},
            timeout=10,
        )
    return requests.patch(
        f"{base_url}/rooms/{room_id}/availability",
        json=data,
        headers=authorization_headers(access_token),
        timeout=10,
    )


def archive_room(base_url, access_token, room_id):
    return requests.delete(
        f"{base_url}/rooms/{room_id}",
        headers=authorization_headers(access_token),
        timeout=10,
    )
