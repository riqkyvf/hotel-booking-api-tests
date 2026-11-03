import string
import pytest


INVALID_EMAIL_CHARACTER_CASES = (
    pytest.param("пользователь@example.com", id="cyrillic_local"),
    pytest.param("user@пример.рф", id="cyrillic_domain"),
    pytest.param("пользователь@пример.рф", id="cyrillic_both"),
    pytest.param("  ПОЛЬЗОВАТЕЛЬ@ПРИМЕР.РФ  ", id="cyrillic_with_outer_spaces"),
    pytest.param("usеr@example.com", id="mixed_script"),
    pytest.param("用户@example.com", id="chinese_local"),
    pytest.param("user@例子.com", id="chinese_domain"),
    pytest.param("user😀@example.com", id="emoji_local"),
    pytest.param("user@😀.com", id="emoji_domain"),
    pytest.param("user name@example.com", id="internal_space"),
    pytest.param("\tuser@example.com", id="leading_tab"),
    pytest.param("user@example.com\n", id="trailing_newline"),
    pytest.param("\u00a0user@example.com", id="nonbreaking_space"),
    pytest.param("user\u200b@example.com", id="zero_width_space"),
    pytest.param("user\x00@example.com", id="null_character"),
    pytest.param("user@example.com\x7f", id="delete_character"),
)


INVALID_PASSWORD_CHARACTER_CASES = (
    pytest.param(" password12345", id="leading_space"),
    pytest.param("password12345 ", id="trailing_space"),
    pytest.param("password 12345", id="internal_space"),
    pytest.param(" " * 10, id="only_spaces"),
    pytest.param("ПарольДляТеста", id="cyrillic"),
    pytest.param("ПарольTest123", id="mixed_script"),
    pytest.param("TestPassword123а", id="confusable"),
    pytest.param("я" * 10, id="cyrillic_min_length"),
    pytest.param("я" * 128, id="cyrillic_max_length"),
    pytest.param("Password用户12", id="chinese"),
    pytest.param("Password😀123", id="emoji"),
    pytest.param("\tpassword12345", id="leading_tab"),
    pytest.param("password12345\n", id="trailing_newline"),
    pytest.param("password12345\r", id="carriage_return"),
    pytest.param("Password\u00a0123", id="nonbreaking_space"),
    pytest.param("Password\u200b123", id="zero_width_space"),
    pytest.param("password12345\x00", id="null_character"),
    pytest.param("password12345\x7f", id="delete_character"),
)


ASCII_EMAIL_DOMAINS = ("example.com", "xn--e1afmkfd.xn--p1ai")


VALID_ASCII_PASSWORD_CASES = (
    pytest.param("a" * 10, id="min_length_letters_only"),
    pytest.param("a" * 128, id="max_length_letters_only"),
    pytest.param("A" * 10, id="uppercase_only"),
    pytest.param("1234567890", id="digits_only"),
    pytest.param(string.punctuation, id="punctuation_only"),
    pytest.param(
        string.ascii_letters + string.digits + string.punctuation,
        id="all_printable_ascii_without_space",
    ),
)
