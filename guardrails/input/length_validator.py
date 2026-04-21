from config.constants import MAX_QUERY_LENGTH, MIN_QUERY_LENGTH
from guardrails.models import GuardrailResult


def check_length(query: str) -> GuardrailResult:
    length = len(query.strip())
    if length < MIN_QUERY_LENGTH:
        return GuardrailResult(
            passed=False,
            block_code="QUERY_TOO_SHORT",
            reason=f"Query must be at least {MIN_QUERY_LENGTH} characters.",
        )
    if length > MAX_QUERY_LENGTH:
        return GuardrailResult(
            passed=False,
            block_code="QUERY_TOO_LONG",
            reason=f"Query exceeds the {MAX_QUERY_LENGTH}-character limit.",
        )
    return GuardrailResult(passed=True)
