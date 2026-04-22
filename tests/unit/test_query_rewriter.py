"""Unit tests for graph/nodes/query_rewriter.py."""

from unittest.mock import patch

import pytest

from graph.nodes.query_rewriter import query_rewriter_node


def _state(**kw):
    return {
        "query": "alerts",
        "rewritten_query": "",
        "documents": [],
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


def test_query_rewriter_increments_rewrite_count():
    with patch("graph.nodes.query_rewriter.grade", return_value=("How to configure SNMP alerts?", {})):
        result = query_rewriter_node(_state(rewrite_count=1))
    assert result["rewrite_count"] == 2


def test_query_rewriter_sets_rewritten_query():
    rewritten = "How do I set up SNMP alert destinations in OME?"
    with patch("graph.nodes.query_rewriter.grade", return_value=(rewritten, {})):
        result = query_rewriter_node(_state())
    assert result["rewritten_query"] == rewritten


def test_query_rewriter_strips_whitespace_from_response():
    with patch("graph.nodes.query_rewriter.grade", return_value=("  rewritten query  ", {})):
        result = query_rewriter_node(_state())
    assert result["rewritten_query"] == "rewritten query"


def test_query_rewriter_starts_from_zero():
    with patch("graph.nodes.query_rewriter.grade", return_value=("new query", {})):
        result = query_rewriter_node(_state(rewrite_count=0))
    assert result["rewrite_count"] == 1
