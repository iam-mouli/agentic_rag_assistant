"""
Integration tests for the happy-path retrieve flow through the LangGraph.

Flow: Router → Retriever → DocGrader → Generator → HallucinationGrader → AnswerGrader → END
LLM calls mocked. Real SQLite + real FAISS index (seeded_tenant fixture).
"""

import pytest

from config.constants import ANSWER_SCORE_THRESHOLD, HALLUCINATION_THRESHOLD
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
async def test_retrieve_path_returns_answer_with_citations(seeded_tenant, mock_llm):
    state = _initial_state("How do I configure the system?", seeded_tenant["name"])
    result = await rag_graph.ainvoke(state)

    assert result["generation"] == "Mock generated answer about configuration."
    assert result["fallback"] is False
    assert len(result["citations"]) > 0


@pytest.mark.asyncio
async def test_retrieve_path_passes_hallucination_check(seeded_tenant, mock_llm):
    state = _initial_state("How do I configure the system?", seeded_tenant["name"])
    result = await rag_graph.ainvoke(state)

    assert result["hallucination_score"] >= HALLUCINATION_THRESHOLD


@pytest.mark.asyncio
async def test_retrieve_path_passes_answer_quality_check(seeded_tenant, mock_llm):
    state = _initial_state("How do I configure the system?", seeded_tenant["name"])
    result = await rag_graph.ainvoke(state)

    assert result["answer_score"] >= ANSWER_SCORE_THRESHOLD


@pytest.mark.asyncio
async def test_retrieve_path_sets_route_decision_retrieve(seeded_tenant, mock_llm):
    state = _initial_state("How do I configure SNMP alerts?", seeded_tenant["name"])
    result = await rag_graph.ainvoke(state)

    assert result["route_decision"] == "retrieve"


@pytest.mark.asyncio
async def test_retrieve_path_no_rewrites_on_happy_path(seeded_tenant, mock_llm):
    state = _initial_state("How do I configure the system?", seeded_tenant["name"])
    result = await rag_graph.ainvoke(state)

    assert result["rewrite_count"] == 0
