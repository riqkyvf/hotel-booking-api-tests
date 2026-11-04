import requests


def get_liveness(base_url):
    return requests.get(f"{base_url}/health/live", timeout=10)


def get_readiness(base_url):
    return requests.get(f"{base_url}/health/ready", timeout=10)
