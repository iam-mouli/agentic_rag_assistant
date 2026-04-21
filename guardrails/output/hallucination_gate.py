from config.constants import HALLUCINATION_THRESHOLD
from guardrails.models import GuardrailResult


def check_hallucination(result: dict) -> GuardrailResult:
    # Fallback answers are not grounded in docs; gate doesn't apply.
    if result.get("fallback"):
        return GuardrailResult(passed=True)

    score = result.get("hallucination_score", 0.0)
    if score < HALLUCINATION_THRESHOLD:
        return GuardrailResult(
            passed=False,
            block_code="HALLUCINATION_RISK",
            reason=(
                f"Hallucination score {score:.2f} is below the "
                f"{HALLUCINATION_THRESHOLD} threshold."
            ),
        )
    return GuardrailResult(passed=True)
