import re

from guardrails.models import GuardrailResult

_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.I),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)", re.I),
    re.compile(r"forget\s+(all\s+)?previous\s+instructions?", re.I),
    re.compile(r"you\s+are\s+now\s+(?:a|an|the)\s+\w+", re.I),
    re.compile(r"(act|pretend|behave)\s+as\s+(if\s+you\s+are|a|an)\b", re.I),
    re.compile(r"new\s+instructions?\s*:", re.I),
    re.compile(r"system\s*prompt\s*:", re.I),
    re.compile(r"override\s+(system|safety|instructions?)", re.I),
    re.compile(r"jailbreak", re.I),
    re.compile(r"do\s+anything\s+now\b", re.I),        # DAN prompt
    re.compile(r"\[system\]", re.I),
    re.compile(r"<\s*/?system\s*>", re.I),
]


def check_injection(query: str) -> GuardrailResult:
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(query):
            return GuardrailResult(
                passed=False,
                block_code="INJECTION_DETECTED",
                reason="Query contains a suspected prompt injection pattern.",
            )
    return GuardrailResult(passed=True)
