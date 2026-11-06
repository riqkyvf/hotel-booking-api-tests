import pytest


VALID_PROFILE_FIELD_CHANGES = (
    pytest.param("name", "  Changed Name  ", "Changed Name", id="trim_name"),
    pytest.param("name", "  a  ", "a", id="min_name_after_trim"),
    pytest.param("name", "  " + "a" * 100 + "  ", "a" * 100, id="max_name_after_trim"),
    pytest.param("name", "Евгений", "Евгений", id="cyrillic_name"),
    pytest.param("name", "Anna Maria", "Anna Maria", id="internal_name_space"),
    pytest.param("phone", "7" * 7, "7" * 7, id="min_phone"),
    pytest.param("phone", "+" + "7" * 7, "+" + "7" * 7, id="min_phone_with_plus"),
    pytest.param("phone", "7" * 15, "7" * 15, id="max_phone"),
    pytest.param("phone", "+" + "7" * 15, "+" + "7" * 15, id="max_phone_with_plus"),
)


INVALID_PROFILE_CHANGES = (
    pytest.param({"email": None}, "body.email", id="null_email"),
    pytest.param({"name": None}, None, id="null_name"),
    pytest.param({"email": ""}, "body.email", id="empty_email"),
    pytest.param({"email": "   "}, "body.email", id="spaces_email"),
    pytest.param({"email": "userexample.com"}, "body.email", id="email_without_at"),
    pytest.param({"email": "user@"}, "body.email", id="email_without_domain"),
    pytest.param({"email": "@example.com"}, "body.email", id="email_without_local_part"),
    pytest.param({"name": ""}, "body.name", id="empty_name"),
    pytest.param({"name": "   "}, "body.name", id="spaces_name"),
    pytest.param({"name": "a" * 101}, "body.name", id="long_name"),
    pytest.param({"phone": ""}, "body.phone", id="empty_phone"),
    pytest.param({"phone": "   "}, "body.phone", id="spaces_phone"),
    pytest.param({"phone": "7" * 6}, "body.phone", id="short_phone"),
    pytest.param({"phone": "+" + "7" * 6}, "body.phone", id="short_phone_with_plus"),
    pytest.param({"phone": "7" * 16}, "body.phone", id="long_phone"),
    pytest.param({"phone": "+" + "7" * 16}, "body.phone", id="long_phone_with_plus"),
    pytest.param({"phone": "+7999abc4567"}, "body.phone", id="letters_in_phone"),
    pytest.param({"phone": "7999 1234567"}, "body.phone", id="space_in_phone"),
    pytest.param({"phone": "7999-1234567"}, "body.phone", id="hyphen_in_phone"),
    pytest.param({"phone": "(7999)1234567"}, "body.phone", id="parentheses_in_phone"),
    pytest.param({"phone": "++79991234567"}, "body.phone", id="double_plus"),
    pytest.param({"phone": "79991234567+"}, "body.phone", id="trailing_plus"),
    pytest.param({"phone": "１２３４５６７"}, "body.phone", id="non_ascii_phone_digits"),
)


INVALID_PROFILE_FIELD_TYPES = (
    pytest.param(1234567890, id="integer"),
    pytest.param(1234567890.5, id="float"),
    pytest.param(True, id="true"),
    pytest.param(False, id="false"),
    pytest.param([], id="array"),
    pytest.param({}, id="object"),
)


FORBIDDEN_PROFILE_FIELDS = (
    pytest.param("role", "admin", id="role"),
    pytest.param("is_active", False, id="is_active"),
    pytest.param("password", "ChangedPassword123!", id="password"),
    pytest.param("password_hash", "some-value", id="password_hash"),
    pytest.param("id", "e2e186d6-7682-466a-812e-b6367d9e4343", id="id"),
    pytest.param("user_id", "e2e186d6-7682-466a-812e-b6367d9e4343", id="user_id"),
    pytest.param("created_at", "2026-11-03T00:00:00Z", id="created_at"),
    pytest.param("updated_at", "2026-11-03T00:00:00Z", id="updated_at"),
    pytest.param("unexpected", "value", id="unexpected"),
)


INVALID_PROFILE_BODIES = (
    pytest.param("{}", id="empty_object"),
    pytest.param('{"name":', id="malformed_json"),
    pytest.param("[]", id="array"),
)


INVALID_PROFILE_ACCESS_TOKENS = (
    pytest.param(None, id="no_authorization_header"),
    pytest.param("", id="empty_bearer"),
    pytest.param("invalid-token", id="malformed_token"),
)
