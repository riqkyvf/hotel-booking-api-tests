import requests

from api.headers import authorization_headers


def get_profile(base_url, access_token):
    return requests.get(
        f"{base_url}/users/me",
        headers=authorization_headers(access_token),
        timeout=10,
    )


def update_profile(base_url, access_token, data=None, *, raw_body=None):
    headers = authorization_headers(access_token)

    if raw_body is not None:
        headers["Content-Type"] = "application/json"
        return requests.patch(
            f"{base_url}/users/me",
            data=raw_body,
            headers=headers,
            timeout=10,
        )

    return requests.patch(
        f"{base_url}/users/me",
        json=data,
        headers=headers,
        timeout=10,
    )


def update_user_as_admin(base_url, access_token, user_id, data=None, *, raw_body=None):
    if raw_body is not None:
        return requests.patch(
            f"{base_url}/admin/users/{user_id}", data=raw_body,
            headers={**authorization_headers(access_token), "Content-Type": "application/json"},
            timeout=10,
        )
    return requests.patch(
        f"{base_url}/admin/users/{user_id}",
        json=data,
        headers=authorization_headers(access_token),
        timeout=10,
    )


def list_users_as_admin(base_url, access_token, params=None):
    return requests.get(
        f"{base_url}/admin/users",
        params=params,
        headers=authorization_headers(access_token),
        timeout=10,
    )


def get_user_as_admin(base_url, access_token, user_id):
    return requests.get(
        f"{base_url}/admin/users/{user_id}",
        headers=authorization_headers(access_token),
        timeout=10,
    )
