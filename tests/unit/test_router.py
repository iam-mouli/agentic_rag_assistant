"""Unit tests for graph/nodes/router.py."""

from unittest.mock import patch

import pytest

from graph.nodes.router import router_node


def _state(**kw):
    return {
        "query": "How do I configure SNMP alerts?",
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


def test_router_returns_retrieve_for_domain_query():
    with patch("graph.nodes.router.grade", return_value=("retrieve", {})):
        result = router_node(_state())
    assert result["route_decision"] == "retrieve"


def test_router_returns_direct_answer_for_general_query():
    with patch("graph.nodes.router.grade", return_value=("direct_answer", {})):
        result = router_node(_state(query="What year was Dell founded?"))
    assert result["route_decision"] == "direct_answer"


def test_router_defaults_to_retrieve_on_ambiguous_response():
    # Response containing neither keyword → falls back to retrieve
    with patch("graph.nodes.router.grade", return_value=("unclear", {})):
        result = router_node(_state())
    assert result["route_decision"] == "retrieve"
