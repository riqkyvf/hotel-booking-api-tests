import string
import pytest


INVALID_EMAIL_CHARACTER_CASES = (
    pytest.param("пользователь@example.com", id="cyrillic_local"),
    pytest.param("user@пример.рф", id="cyrillic_domain"),
    pytest.param("user name@example.com", id="internal_space"),
    pytest.param("\tuser@example.com", id="leading_tab"),
    pytest.param("user\u200b@example.com", id="zero_width_space"),
)


INVALID_PASSWORD_CHARACTER_CASES = (
    pytest.param("password12345 ", id="trailing_space"),
    pytest.param("password 12345", id="internal_space"),
    pytest.param("ПарольДляТеста", id="cyrillic"),
    pytest.param("password12345\n", id="trailing_newline"),
)


ASCII_EMAIL_DOMAINS = ("example.com", "xn--e1afmkfd.xn--p1ai")


VALID_ASCII_PASSWORD_CASES = (
    pytest.param("a" * 10, id="min_length_letters_only"),
    pytest.param("a" * 128, id="max_length_letters_only"),
    pytest.param("1234567890", id="digits_only"),
    pytest.param(string.punctuation, id="punctuation_only"),
)
