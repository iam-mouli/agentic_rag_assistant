"""Unit tests for all output guardrails and the output pipeline."""

import pytest

from config.constants import ANSWER_SCORE_THRESHOLD, HALLUCINATION_THRESHOLD
from guardrails.output import run_output_guardrails
from guardrails.output.citation_enforcer import check_citations
from guardrails.output.confidence_tagger import check_confidence, tag_confidence
from guardrails.output.hallucination_gate import check_hallucination


# ---------------------------------------------------------------------------
# HallucinationGate
# ---------------------------------------------------------------------------

def test_hallucination_gate_blocks_below_threshold():
    result = check_hallucination({
        "hallucination_score": HALLUCINATION_THRESHOLD - 0.01,
        "fallback": False,
    })
    assert not result.passed
    assert result.block_code == "HALLUCINATION_RISK"


def test_hallucination_gate_passes_above_threshold():
    result = check_hallucination({
        "hallucination_score": HALLUCINATION_THRESHOLD + 0.01,
        "fallback": False,
    })
    assert result.passed


def test_hallucination_gate_passes_at_exact_threshold():
    result = check_hallucination({
        "hallucination_score": HALLUCINATION_THRESHOLD,
        "fallback": False,
    })
    assert result.passed


def test_hallucination_gate_skips_fallback_answers():
    # Fallback answers have score 0.0 but gate must not block them
    result = check_hallucination({"hallucination_score": 0.0, "fallback": True})
    assert result.passed


# ---------------------------------------------------------------------------
# CitationEnforcer
# ---------------------------------------------------------------------------

def test_citation_enforcer_blocks_empty_citations_on_rag_path():
    result = check_citations({
        "route_decision": "retrieve",
        "citations": [],
        "fallback": False,
    })
    assert not result.passed
    assert result.block_code == "MISSING_CITATIONS"


def test_citation_enforcer_skips_direct_answer_path():
    result = check_citations({
        "route_decision": "direct_answer",
        "citations": [],
        "fallback": False,
    })
    assert result.passed


def test_citation_enforcer_skips_fallback_response():
    result = check_citations({
        "route_decision": "retrieve",
        "citations": [],
        "fallback": True,
    })
    assert result.passed


def test_citation_enforcer_passes_with_at_least_one_citation():
    result = check_citations({
        "route_decision": "retrieve",
        "citations": [{"doc_id": "d1", "filename": "guide.pdf", "page": 5}],
        "fallback": False,
    })
    assert result.passed


# ---------------------------------------------------------------------------
# ConfidenceTagger
# ---------------------------------------------------------------------------

def test_confidence_tagger_returns_high_above_085():
    assert tag_confidence(0.90) == "high"
    assert tag_confidence(0.85) == "high"


def test_confidence_tagger_returns_medium_between_thresholds():
    assert tag_confidence(0.75) == "medium"
    assert tag_confidence(ANSWER_SCORE_THRESHOLD) == "medium"


def test_confidence_tagger_returns_low_below_threshold():
    assert tag_confidence(0.50) == "low"
    assert tag_confidence(0.00) == "low"


def test_confidence_check_always_passes():
    # check_confidence is a metadata side-channel — must never block
    result = check_confidence({"answer_score": 0.0})
    assert result.passed


# ---------------------------------------------------------------------------
# Output pipeline (run_output_guardrails)
# ---------------------------------------------------------------------------

def test_output_pipeline_passes_clean_result():
    result = run_output_guardrails({
        "hallucination_score": 0.88,
        "route_decision": "retrieve",
        "citations": [{"doc_id": "d1", "filename": "f.pdf", "page": 1}],
        "fallback": False,
        "answer_score": 0.80,
    })
    assert result.passed


def test_output_pipeline_blocks_on_hallucination():
    result = run_output_guardrails({
        "hallucination_score": 0.50,  # below 0.75 threshold
        "route_decision": "retrieve",
        "citations": [{"doc_id": "d1"}],
        "fallback": False,
        "answer_score": 0.80,
    })
    assert not result.passed
    assert result.block_code == "HALLUCINATION_RISK"


def test_output_pipeline_blocks_on_missing_citations():
    result = run_output_guardrails({
        "hallucination_score": 0.90,
        "route_decision": "retrieve",
        "citations": [],
        "fallback": False,
        "answer_score": 0.80,
    })
    assert not result.passed
    assert result.block_code == "MISSING_CITATIONS"
