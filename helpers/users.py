import requests


def get_profile(base_url, access_token):
    return requests.get(
        f"{base_url}/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )


def update_user_as_admin(base_url, access_token, user_id, data):
    return requests.patch(
        f"{base_url}/admin/users/{user_id}",
        json=data,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
