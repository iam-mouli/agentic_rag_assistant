"""Unit tests for graph/nodes/hallucination_grader.py."""

from unittest.mock import patch

import pytest
from langchain_core.documents import Document

from config.constants import HALLUCINATION_THRESHOLD
from graph.nodes.hallucination_grader import hallucination_grader_node


def _state(generation="The answer is here.", documents=None, **kw):
    return {
        "query": "How do I configure alerts?",
        "rewritten_query": "",
        "documents": documents or [Document(page_content="Alert config steps.", metadata={})],
        "generation": generation,
        "rewrite_count": 0,
        "hallucination_score": 0.0,
        "answer_score": 0.0,
        "route_decision": "retrieve",
        "citations": [],
        "fallback": False,
        "tenant_id": "ome",
        **kw,
    }


def test_hallucination_grader_scores_grounded_answer():
    with patch("graph.nodes.hallucination_grader.grade", return_value=("0.92", {})):
        result = hallucination_grader_node(_state())
    assert abs(result["hallucination_score"] - 0.92) < 1e-6


def test_hallucination_grader_scores_ungrounded_answer():
    with patch("graph.nodes.hallucination_grader.grade", return_value=("0.15", {})):
        result = hallucination_grader_node(_state(generation="I made this answer up."))
    assert result["hallucination_score"] < HALLUCINATION_THRESHOLD


def test_hallucination_grader_handles_yes_no_response():
    # Non-numeric response: "no" → 0.0
    with patch("graph.nodes.hallucination_grader.grade", return_value=("no", {})):
        result = hallucination_grader_node(_state())
    assert result["hallucination_score"] == 0.0


def test_hallucination_grader_handles_yes_response():
    # Non-numeric response: "yes" → 1.0
    with patch("graph.nodes.hallucination_grader.grade", return_value=("yes", {})):
        result = hallucination_grader_node(_state())
    assert result["hallucination_score"] == 1.0


def test_hallucination_grader_score_above_threshold_passes_gate():
    with patch("graph.nodes.hallucination_grader.grade", return_value=("0.80", {})):
        result = hallucination_grader_node(_state())
    assert result["hallucination_score"] >= HALLUCINATION_THRESHOLD
