HOTEL_SCHEMA = {
    "type": "object",
    "required": [
        "id", "name", "city", "address", "description", "rating",
        "is_archived", "created_at", "updated_at",
    ],
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "city": {"type": "string"},
        "address": {"type": "string"},
        "description": {"type": "string"},
        "rating": {"type": "string"},
        "is_archived": {"type": "boolean"},
        "created_at": {"type": "string"},
        "updated_at": {"type": "string"},
    },
}

HOTEL_PAGE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["items", "total", "limit", "offset"],
    "properties": {
        "items": {"type": "array", "items": HOTEL_SCHEMA},
        "total": {"type": "integer", "minimum": 0},
        "limit": {"type": "integer", "minimum": 1, "maximum": 100},
        "offset": {"type": "integer", "minimum": 0},
    },
}
