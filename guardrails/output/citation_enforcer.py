from guardrails.models import GuardrailResult


def check_citations(result: dict) -> GuardrailResult:
    # Direct-answer path and fallback answers legitimately have no citations.
    route = result.get("route_decision", "retrieve")
    if route == "direct_answer" or result.get("fallback"):
        return GuardrailResult(passed=True)

    citations = result.get("citations") or []
    if not citations:
        return GuardrailResult(
            passed=False,
            block_code="MISSING_CITATIONS",
            reason="RAG response must include at least one source citation.",
        )
    return GuardrailResult(passed=True)
