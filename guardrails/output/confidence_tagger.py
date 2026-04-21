from config.constants import ANSWER_SCORE_THRESHOLD
from guardrails.models import GuardrailResult

_HIGH_THRESHOLD = 0.85
_MED_THRESHOLD = ANSWER_SCORE_THRESHOLD  # 0.70


def tag_confidence(score: float) -> str:
    if score >= _HIGH_THRESHOLD:
        return "high"
    if score >= _MED_THRESHOLD:
        return "medium"
    return "low"


def check_confidence(result: dict) -> GuardrailResult:
    """Always passes — exists to provide the confidence tag as side-channel metadata."""
    return GuardrailResult(passed=True)
