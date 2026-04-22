"""Unit tests for graph/nodes/answer_grader.py."""

from unittest.mock import patch

import pytest

from config.constants import ANSWER_SCORE_THRESHOLD
from graph.nodes.answer_grader import answer_grader_node


def _state(generation="Here is the full answer.", **kw):
    return {
        "query": "How do I configure alerts?",
        "rewritten_query": "",
        "documents": [],
        "generation": generation,
        "rewrite_count": 0,
        "hallucination_score": 0.85,
        "answer_score": 0.0,
        "route_decision": "retrieve",
        "citations": [],
        "fallback": False,
        "tenant_id": "ome",
        **kw,
    }


def test_answer_grader_passes_useful_answer():
    with patch("graph.nodes.answer_grader.grade", return_value=("0.88", {})):
        result = answer_grader_node(_state())
    assert result["answer_score"] >= ANSWER_SCORE_THRESHOLD


def test_answer_grader_fails_unhelpful_answer():
    with patch("graph.nodes.answer_grader.grade", return_value=("0.30", {})):
        result = answer_grader_node(_state(generation="I don't know."))
    assert result["answer_score"] < ANSWER_SCORE_THRESHOLD


def test_answer_grader_handles_yes_response():
    with patch("graph.nodes.answer_grader.grade", return_value=("yes", {})):
        result = answer_grader_node(_state())
    assert result["answer_score"] == 1.0


def test_answer_grader_handles_no_response():
    with patch("graph.nodes.answer_grader.grade", return_value=("no", {})):
        result = answer_grader_node(_state())
    assert result["answer_score"] == 0.0


def test_answer_grader_score_boundary_at_threshold():
    with patch("graph.nodes.answer_grader.grade", return_value=(str(ANSWER_SCORE_THRESHOLD), {})):
        result = answer_grader_node(_state())
    assert abs(result["answer_score"] - ANSWER_SCORE_THRESHOLD) < 1e-6
