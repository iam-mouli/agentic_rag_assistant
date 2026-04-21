import re

from guardrails.models import GuardrailResult

# Patterns clearly outside an enterprise Dell tech knowledge base.
# Policy is permissive — only reject when confidently off-topic.
_OFF_TOPIC_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(recipe|cooking|bake|chef|restaurant|cuisine)\b", re.I),
    re.compile(r"\b(horoscope|zodiac|astrology|tarot)\b", re.I),
    re.compile(r"\b(lottery|gambling|casino|poker|bet)\b", re.I),
    re.compile(r"\b(celebrity|gossip|paparazzi|tabloid)\b", re.I),
    re.compile(r"\b(weight\s*loss|diet\s*pill|supplement)\b", re.I),
    re.compile(r"\b(dating|tinder|romance|pickup\s*line)\b", re.I),
    re.compile(r"\b(write\s*(me\s+a\s+)?poem|love\s+letter)\b", re.I),
]


def check_topic(query: str) -> GuardrailResult:
    for pattern in _OFF_TOPIC_PATTERNS:
        if pattern.search(query):
            return GuardrailResult(
                passed=False,
                block_code="OFF_TOPIC",
                reason="Query appears unrelated to the enterprise knowledge base.",
            )
    return GuardrailResult(passed=True)
