from dataclasses import dataclass, field


@dataclass
class GuardrailResult:
    passed: bool
    block_code: str = ""
    reason: str = ""
