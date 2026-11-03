def authorization_headers(access_token):
    if access_token is None:
        return {}
    return {"Authorization": f"Bearer {access_token}"}
