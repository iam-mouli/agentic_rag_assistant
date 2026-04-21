import re

from guardrails.models import GuardrailResult

_TOXIC_PATTERNS: list[re.Pattern] = [
    re.compile(
        r"\b(kill|murder|bomb|terrorist|genocide|suicide\s+instruction)\b", re.I
    ),
    re.compile(r"\b(fuck|shit|bitch|asshole|bastard)\b", re.I),
    re.compile(r"\b(n[i1]gg[ae]r|f[a4]gg[o0]t|ch[i1]nk|sp[i1]c)\b", re.I),
]


def check_toxicity(result: dict) -> GuardrailResult:
    generation = result.get("generation", "")
    for pattern in _TOXIC_PATTERNS:
        if pattern.search(generation):
            return GuardrailResult(
                passed=False,
                block_code="TOXIC_OUTPUT",
                reason="Generated response contains inappropriate content.",
            )
    return GuardrailResult(passed=True)
