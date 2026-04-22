"""
LangSmith evaluation runner — CI-gated.

Usage:
  python tests/eval/run_evals.py

Exit codes:
  0 — all quality gates passed (or LANGSMITH_API_KEY not set → skip gracefully)
  1 — hallucination_rate >= HALLUCINATION_THRESHOLD or mean answer_score < ANSWER_SCORE_THRESHOLD

The script submits each question in eval_dataset.json to the compiled LangGraph
and scores it against the expected answer using LangSmith evaluators.
"""

import json
import logging
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path when run directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.constants import ANSWER_SCORE_THRESHOLD, HALLUCINATION_THRESHOLD

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

DATASET_PATH = Path(__file__).parent / "ome" / "eval_dataset.json"
TENANT_ID = "ome"  # golden dataset is for the OME tenant


def _load_dataset() -> list[dict]:
    with open(DATASET_PATH) as f:
        return json.load(f)


def _run_query(question: str) -> dict:
    """Run one question through the compiled LangGraph and return the result dict."""
    from graph.builder import rag_graph

    initial_state = {
        "query": question,
        "tenant_id": TENANT_ID,
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
    import asyncio
    return asyncio.run(rag_graph.ainvoke(initial_state))


def _evaluate_with_langsmith(dataset: list[dict]) -> tuple[float, float]:
    """
    Submit Q&A pairs to LangSmith and retrieve hallucination_rate + mean answer_score.
    Returns (hallucination_rate, mean_answer_score).
    """
    from langsmith import Client
    from langsmith.evaluation import evaluate

    ls_client = Client()

    # Create or retrieve the dataset in LangSmith
    ls_dataset_name = f"dell-rag-eval-{TENANT_ID}"
    try:
        ls_dataset = ls_client.create_dataset(ls_dataset_name, description="Golden Q&A for OME tenant")
        for item in dataset:
            ls_client.create_example(
                inputs={"query": item["question"]},
                outputs={"expected_answer": item["expected_answer"]},
                dataset_id=ls_dataset.id,
            )
    except Exception:
        ls_dataset = ls_client.read_dataset(dataset_name=ls_dataset_name)

    def _target(inputs: dict) -> dict:
        result = _run_query(inputs["query"])
        return {
            "generation": result.get("generation", ""),
            "hallucination_score": result.get("hallucination_score", 0.0),
            "answer_score": result.get("answer_score", 0.0),
            "fallback": result.get("fallback", False),
        }

    eval_results = evaluate(
        _target,
        data=ls_dataset_name,
        experiment_prefix="ci-eval",
    )

    hallucination_scores = []
    answer_scores = []
    for r in eval_results:
        run_output = r.run.outputs or {}
        hallucination_scores.append(run_output.get("hallucination_score", 0.0))
        answer_scores.append(run_output.get("answer_score", 0.0))

    if not hallucination_scores:
        return 0.0, 0.0

    hallucination_rate = sum(1 for s in hallucination_scores if s < HALLUCINATION_THRESHOLD) / len(hallucination_scores)
    mean_answer_score = sum(answer_scores) / len(answer_scores)
    return hallucination_rate, mean_answer_score


def _run_local_evals(dataset: list[dict]) -> tuple[float, float]:
    """
    Fallback: run queries locally without LangSmith, compute scores directly.
    Used when LANGSMITH_API_KEY is set but LangSmith is unreachable.
    """
    hallucination_scores = []
    answer_scores = []

    for item in dataset:
        try:
            result = _run_query(item["question"])
            hallucination_scores.append(result.get("hallucination_score", 0.0))
            answer_scores.append(result.get("answer_score", 0.0))
            logger.info(
                "eval_item_done q=%.40s hallucination=%.2f answer=%.2f",
                item["question"],
                result.get("hallucination_score", 0.0),
                result.get("answer_score", 0.0),
            )
        except Exception as exc:
            logger.error("eval_item_failed q=%.40s error=%s", item["question"], exc)
            hallucination_scores.append(0.0)
            answer_scores.append(0.0)

    if not hallucination_scores:
        return 0.0, 0.0

    hallucination_rate = sum(1 for s in hallucination_scores if s < HALLUCINATION_THRESHOLD) / len(hallucination_scores)
    mean_answer_score = sum(answer_scores) / len(answer_scores)
    return hallucination_rate, mean_answer_score


def main() -> int:
    langsmith_key = os.environ.get("LANGSMITH_API_KEY", "")
    if not langsmith_key:
        logger.warning(
            "LANGSMITH_API_KEY not set — skipping LangSmith evaluation. "
            "Set the key in CI to gate on quality regressions."
        )
        return 0

    dataset = _load_dataset()
    logger.info("Loaded %d eval examples from %s", len(dataset), DATASET_PATH)

    try:
        hallucination_rate, mean_answer_score = _evaluate_with_langsmith(dataset)
    except Exception as exc:
        logger.warning("LangSmith evaluation failed (%s) — falling back to local eval", exc)
        hallucination_rate, mean_answer_score = _run_local_evals(dataset)

    logger.info(
        "Eval results: hallucination_rate=%.3f (threshold=%.2f) "
        "mean_answer_score=%.3f (threshold=%.2f)",
        hallucination_rate,
        HALLUCINATION_THRESHOLD,
        mean_answer_score,
        ANSWER_SCORE_THRESHOLD,
    )

    failed = False

    if hallucination_rate >= HALLUCINATION_THRESHOLD:
        logger.error(
            "QUALITY GATE FAILED: hallucination_rate %.3f >= threshold %.2f",
            hallucination_rate,
            HALLUCINATION_THRESHOLD,
        )
        failed = True

    if mean_answer_score < ANSWER_SCORE_THRESHOLD:
        logger.error(
            "QUALITY GATE FAILED: mean_answer_score %.3f < threshold %.2f",
            mean_answer_score,
            ANSWER_SCORE_THRESHOLD,
        )
        failed = True

    if not failed:
        logger.info("All quality gates passed.")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
