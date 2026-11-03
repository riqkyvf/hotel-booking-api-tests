ROOM_SCHEMA = {
    "type": "object",
    "required": ["id", "hotel_id", "room_number", "type", "capacity", "price_per_night",
                 "is_available", "is_archived", "created_at", "updated_at"],
    "properties": {
        "id": {"type": "string", "format": "uuid"},
        "hotel_id": {"type": "string", "format": "uuid"},
        "room_number": {"type": "string", "minLength": 1, "maxLength": 20},
        "type": {"enum": ["single", "double", "twin", "family", "suite"]},
        "capacity": {"type": "integer", "minimum": 1, "maximum": 10},
        "price_per_night": {"type": "string", "pattern": r"^[0-9]+\.[0-9]{2}$"},
        "is_available": {"type": "boolean"},
        "is_archived": {"type": "boolean"},
        "created_at": {"type": "string", "format": "date-time"},
        "updated_at": {"type": "string", "format": "date-time"},
    },
}
