from guardrails.output.hallucination_gate import check_hallucination
from guardrails.output.citation_enforcer import check_citations
from guardrails.output.toxicity_filter import check_toxicity
from guardrails.output.confidence_tagger import check_confidence
from guardrails.models import GuardrailResult

_PIPELINE = [check_hallucination, check_citations, check_toxicity, check_confidence]


def run_output_guardrails(result: dict) -> GuardrailResult:
    for check in _PIPELINE:
        gr = check(result)
        if not gr.passed:
            return gr
    return GuardrailResult(passed=True)
