from guardrails.input.length_validator import check_length
from guardrails.input.injection_detector import check_injection
from guardrails.input.pii_filter import check_pii
from guardrails.input.topic_checker import check_topic
from guardrails.models import GuardrailResult

# Ordered cheapest → most expensive; short-circuits on first failure.
_PIPELINE = [check_length, check_injection, check_pii, check_topic]


def run_input_guardrails(query: str) -> GuardrailResult:
    for check in _PIPELINE:
        result = check(query)
        if not result.passed:
            return result
    return GuardrailResult(passed=True)
