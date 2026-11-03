PAYMENT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["id", "booking_id", "amount", "currency", "status", "failure_reason", "created_at", "updated_at"],
    "properties": {
        "id": {"type": "string", "format": "uuid"},
        "booking_id": {"type": "string", "format": "uuid"},
        "amount": {"type": "string", "pattern": r"^(?:0|[1-9][0-9]*)\.[0-9]{2}$"},
        "currency": {"const": "RUB"},
        "status": {"enum": ["pending", "succeeded", "failed", "cancelled", "refunded"]},
        "failure_reason": {"type": ["string", "null"]},
        "created_at": {"type": "string", "format": "date-time"},
        "updated_at": {"type": "string", "format": "date-time"},
    },
    "if": {"properties": {"status": {"const": "failed"}}},
    "then": {"properties": {"failure_reason": {"type": "string", "minLength": 1, "maxLength": 250}}},
    "else": {"properties": {"failure_reason": {"type": "null"}}},
}
