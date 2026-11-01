ERROR_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["error"],
    "properties": {
        "error": {
            "type": "object",
            "required": ["code", "message", "details", "request_id"],
            "properties": {
                "code": {"type": "string"},
                "message": {"type": "string"},
                "request_id": {"type": "string"},
                "details": {
                    "type": "array",
                    "items": {"type": "object"},
                },
            },
            "if": {
                "properties": {"code": {"const": "VALIDATION_ERROR"}},
            },
            "then": {
                "properties": {
                    "details": {
                        "items": {
                            "required": ["field", "message", "type"],
                            "properties": {
                                "field": {"type": "string"},
                                "message": {"type": "string"},
                                "type": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
    },
}
