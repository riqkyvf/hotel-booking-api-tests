import requests


def get_profile(base_url, access_token):
    return requests.get(
        f"{base_url}/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )


def update_profile(base_url, access_token, data=None, *, raw_body=None):
    headers = {}
    if access_token is not None:
        headers["Authorization"] = f"Bearer {access_token}"

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


def update_user_as_admin(base_url, access_token, user_id, data):
    return requests.patch(
        f"{base_url}/admin/users/{user_id}",
        json=data,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
