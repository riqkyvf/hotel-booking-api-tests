import pytest


PAYMENT_DECLINE_REASON = "Simulated insufficient funds"

PAYMENT_FAILURE_CASES = (
    pytest.param({"reason": PAYMENT_DECLINE_REASON}, PAYMENT_DECLINE_REASON, id="custom_reason"),
    pytest.param({}, "Simulated decline", id="default_reason"),
)
