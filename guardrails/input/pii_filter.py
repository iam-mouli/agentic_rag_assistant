import re
from typing import Sequence

from guardrails.models import GuardrailResult

_PII_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("CREDIT_CARD", re.compile(r"\b(?:\d[ -]?){13,16}\b")),
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    ("PHONE_US", re.compile(r"\b(?:\+1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}\b")),
    ("PASSPORT", re.compile(r"\b[A-Z]{1,2}\d{6,9}\b")),
]


def check_pii(query: str) -> GuardrailResult:
    for label, pattern in _PII_PATTERNS:
        if pattern.search(query):
            return GuardrailResult(
                passed=False,
                block_code="PII_DETECTED",
                reason=f"Query appears to contain {label} — remove sensitive data before querying.",
            )
    return GuardrailResult(passed=True)
