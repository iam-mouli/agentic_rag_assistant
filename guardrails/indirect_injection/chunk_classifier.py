import re

# Patterns that suggest a document chunk is attempting to inject instructions
# into the LLM when it is used as retrieved context.
_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.I),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)", re.I),
    re.compile(r"forget\s+(all\s+)?previous\s+instructions?", re.I),
    re.compile(r"you\s+are\s+now\s+(?:a|an|the)\s+\w+", re.I),
    re.compile(r"new\s+(system\s+)?instructions?\s*:", re.I),
    re.compile(r"system\s*prompt\s*:", re.I),
    re.compile(r"<\s*/?system\s*>", re.I),
    re.compile(r"\[system\]", re.I),
    re.compile(r"override\s+(safety|system|instructions?)", re.I),
    # Data-exfiltration attempts via markdown/links
    re.compile(r"\!\[.*?\]\(https?://", re.I),
    re.compile(r"send\s+.{0,30}\s+to\s+https?://", re.I),
]


def classify_chunk(text: str) -> bool:
    """Return True if chunk is safe to index, False if it should be quarantined."""
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return False
    return True
