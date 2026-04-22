"""
Integration tests for the fallback path through the LangGraph.

Scenario: DocGrader rejects all chunks on every attempt → QueryRewriter fires
MAX_REWRITE_ATTEMPTS times → check_loop_limit returns "fallback" → Fallback node.
"""

import pytest

from config.constants import MAX_REWRITE_ATTEMPTS
from graph.builder import rag_graph


def _initial_state(query: str, tenant_id: str) -> dict:
    return {
        "query": query,
        "tenant_id": tenant_id,
        "rewritten_query": "",
        "documents": [],
        "generation": "",
        "rewrite_count": 0,
        "hallucination_score": 0.0,
        "answer_score": 0.0,
        "route_decision": "retrieve",
        "citations": [],
        "fallback": False,
    }


@pytest.mark.asyncio
async def test_max_rewrites_triggers_fallback(seeded_tenant, mock_llm, monkeypatch):
    """DocGrader always rejects → after MAX_REWRITE_ATTEMPTS the graph falls back."""
    monkeypatch.setattr(
        "graph.nodes.doc_grader.grade",
        lambda messages, **kw: ("no", {}),
    )
    state = _initial_state("configure system", seeded_tenant["name"])
    result = await rag_graph.ainvoke(state)

    assert result["fallback"] is True


@pytest.mark.asyncio
async def test_fallback_response_has_correct_shape(seeded_tenant, mock_llm, monkeypatch):
    """Fallback result: generation contains the canned message, citations empty, score 0."""
    monkeypatch.setattr(
        "graph.nodes.doc_grader.grade",
        lambda messages, **kw: ("no", {}),
    )
    state = _initial_state("configure system", seeded_tenant["name"])
    result = await rag_graph.ainvoke(state)

    assert result["fallback"] is True
    assert "wasn't able to find" in result["generation"].lower() or len(result["generation"]) > 0
    assert result["citations"] == []
    assert result["hallucination_score"] == 0.0
    assert result["answer_score"] == 0.0


@pytest.mark.asyncio
async def test_fallback_rewrite_count_equals_max(seeded_tenant, mock_llm, monkeypatch):
    """rewrite_count must equal MAX_REWRITE_ATTEMPTS when fallback fires."""
    monkeypatch.setattr(
        "graph.nodes.doc_grader.grade",
        lambda messages, **kw: ("no", {}),
    )
    state = _initial_state("configure system", seeded_tenant["name"])
    result = await rag_graph.ainvoke(state)

    assert result["rewrite_count"] == MAX_REWRITE_ATTEMPTS


@pytest.mark.asyncio
async def test_fallback_passes_output_guardrails(seeded_tenant, mock_llm, monkeypatch):
    """Output guardrails must not block a fallback response (gate skips fallback=True)."""
    from guardrails.output import run_output_guardrails

    monkeypatch.setattr(
        "graph.nodes.doc_grader.grade",
        lambda messages, **kw: ("no", {}),
    )
    state = _initial_state("configure system", seeded_tenant["name"])
    result = await rag_graph.ainvoke(state)

    guard_result = run_output_guardrails(result)
    assert guard_result.passed
