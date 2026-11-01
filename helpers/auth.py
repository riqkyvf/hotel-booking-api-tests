import requests


def register(base_url, data):
    return requests.post(
        f"{base_url}/auth/register",
        json=data,
        timeout=10,
    )


def login(base_url, data):
    return requests.post(
        f"{base_url}/auth/login",
        json=data,
        timeout=10,
    )
