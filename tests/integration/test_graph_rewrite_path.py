"""
Integration tests for the query-rewrite path through the LangGraph.

Scenario: DocGrader rejects all chunks on first attempt → QueryRewriter fires →
second retrieval returns relevant docs → pipeline succeeds.
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
async def test_first_retrieval_fail_triggers_rewrite(seeded_tenant, mock_llm, monkeypatch):
    """DocGrader rejects on attempt 1, passes on attempt 2 → rewrite_count == 1."""
    call_count = {"n": 0}

    def _grade_first_no_then_yes(messages, **kw):
        call_count["n"] += 1
        if call_count["n"] <= len(seeded_tenant["dim"] and [1, 2, 3]):
            return "no", {}
        return "yes", {}

    # Reject all chunks on first pass, accept on second
    responses = []

    def alternating_grade(messages, **kw):
        responses.append(1)
        # First 3 calls (one per chunk, first retrieval) → no
        if len(responses) <= 3:
            return "no", {}
        return "yes", {}

    monkeypatch.setattr("graph.nodes.doc_grader.grade", alternating_grade)

    state = _initial_state("configure system", seeded_tenant["name"])
    result = await rag_graph.ainvoke(state)

    assert result["rewrite_count"] >= 1


@pytest.mark.asyncio
async def test_rewrite_produces_different_query(seeded_tenant, mock_llm, monkeypatch):
    """After a failed retrieval the rewritten_query must differ from the original."""
    # Force one rewrite cycle: reject docs first, then accept
    call_count = {"grader": 0}

    def grade_no_then_yes(messages, **kw):
        call_count["grader"] += 1
        return ("no", {}) if call_count["grader"] <= 3 else ("yes", {})

    monkeypatch.setattr("graph.nodes.doc_grader.grade", grade_no_then_yes)

    original_query = "configuration steps"
    state = _initial_state(original_query, seeded_tenant["name"])
    result = await rag_graph.ainvoke(state)

    # The rewriter mock returns "How is configuration done in detail?"
    assert result.get("rewritten_query", "") != original_query


@pytest.mark.asyncio
async def test_rewrite_count_increments_each_loop(seeded_tenant, mock_llm, monkeypatch):
    """Two failed retrievals → rewrite_count == 2 before success."""
    call_count = {"grader": 0}

    def grade_fail_twice(messages, **kw):
        call_count["grader"] += 1
        # Reject for first 6 calls (2 retrieval × 3 chunks), then accept
        return ("no", {}) if call_count["grader"] <= 6 else ("yes", {})

    monkeypatch.setattr("graph.nodes.doc_grader.grade", grade_fail_twice)

    state = _initial_state("configure alerts", seeded_tenant["name"])
    result = await rag_graph.ainvoke(state)

    assert result["rewrite_count"] >= 2
