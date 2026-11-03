from jsonschema import validate

from schemas.error_response import ERROR_SCHEMA


def assert_api_error(response, *, status, code):
    """Check the shared error contract and return the body for scenario checks."""
    assert response.status_code == status, response.text
    body = response.json()
    validate(instance=body, schema=ERROR_SCHEMA)
    assert body["error"]["code"] == code
    assert response.headers.get("X-Request-ID")
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]
    return body
