import requests

def register(base_url, data=None, *, raw_body=None):
    if raw_body is not None:
        return requests.post(
            f"{base_url}/auth/register",
            data=raw_body,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

    return requests.post(
        f"{base_url}/auth/register",
        json=data,
        timeout=10,
    )


def login(base_url, data=None, *, raw_body=None):
    if raw_body is not None:
        return requests.post(
            f"{base_url}/auth/login",
            data=raw_body,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

    return requests.post(
        f"{base_url}/auth/login",
        json=data,
        timeout=10,
    )
