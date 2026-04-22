"""Unit tests for graph/nodes/doc_grader.py."""

from unittest.mock import patch

import pytest
from langchain_core.documents import Document

from graph.nodes.doc_grader import doc_grader_node


def _state(documents=None, **kw):
    return {
        "query": "How do I configure SNMP alerts?",
        "rewritten_query": "",
        "documents": documents or [],
        "generation": "",
        "rewrite_count": 0,
        "hallucination_score": 0.0,
        "answer_score": 0.0,
        "route_decision": "retrieve",
        "citations": [],
        "fallback": False,
        "tenant_id": "ome",
        **kw,
    }


def _doc(content, **meta):
    return Document(
        page_content=content,
        metadata={"doc_id": "d1", "filename": "guide.pdf", "page": 1, **meta},
    )


def test_doc_grader_filters_irrelevant_chunks():
    docs = [_doc("A cake recipe with flour and sugar."), _doc("Holiday travel tips.")]
    with patch("graph.nodes.doc_grader.grade", return_value=("no", {})):
        result = doc_grader_node(_state(documents=docs))
    assert result["documents"] == []


def test_doc_grader_passes_relevant_chunks():
    docs = [_doc("SNMP alert configuration in OME."), _doc("Alert destination setup guide.")]
    with patch("graph.nodes.doc_grader.grade", return_value=("yes", {})):
        result = doc_grader_node(_state(documents=docs))
    assert len(result["documents"]) == 2


def test_doc_grader_partial_filter():
    """One chunk relevant, one not — grader called per chunk."""
    docs = [_doc("Relevant config info."), _doc("Unrelated content.")]
    responses = iter([("yes", {}), ("no", {})])
    with patch("graph.nodes.doc_grader.grade", side_effect=lambda m, **kw: next(responses)):
        result = doc_grader_node(_state(documents=docs))
    assert len(result["documents"]) == 1


def test_doc_grader_empty_documents_returns_empty():
    result = doc_grader_node(_state(documents=[]))
    assert result["documents"] == []


def test_doc_grader_uses_rewritten_query_when_available():
    """When rewritten_query is set it should be used for grading, not the original."""
    docs = [_doc("Alert setup steps.")]
    captured = []

    def spy_grade(messages, **kw):
        captured.append(messages)
        return "yes", {}

    state = _state(
        documents=docs,
        query="alerts?",
        rewritten_query="How to configure SNMP alert destinations?",
    )
    with patch("graph.nodes.doc_grader.grade", side_effect=spy_grade):
        doc_grader_node(state)

    # The messages should contain the rewritten query, not the short original
    all_content = " ".join(str(m) for m in captured[0])
    assert "How to configure" in all_content
