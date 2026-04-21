from graph.state import GraphState
from config.constants import MAX_REWRITE_ATTEMPTS, HALLUCINATION_THRESHOLD, ANSWER_SCORE_THRESHOLD


def route_query(state: GraphState) -> str:
    """After Router: decide retrieve vs direct_answer."""
    return state.get("route_decision", "retrieve")


def check_direct_answer(state: GraphState) -> str:
    """After Generator: skip graders if this was a direct answer path."""
    if state.get("route_decision") == "direct_answer":
        return "end"
    return "grade"


def grade_documents(state: GraphState) -> str:
    """After DocGrader: proceed to generate if relevant docs exist, else rewrite."""
    return "generate" if state.get("documents") else "rewrite_query"


def check_hallucination(state: GraphState) -> str:
    """After HallucinationGrader: proceed to answer grader if grounded, else rewrite."""
    score = state.get("hallucination_score", 0.0)
    return "grounded" if score >= HALLUCINATION_THRESHOLD else "not_grounded"


def check_answer(state: GraphState) -> str:
    """After AnswerGrader: done if useful, else rewrite."""
    score = state.get("answer_score", 0.0)
    return "useful" if score >= ANSWER_SCORE_THRESHOLD else "not_useful"


def check_loop_limit(state: GraphState) -> str:
    """After QueryRewriter: continue to retriever or trigger fallback."""
    return "fallback" if state.get("rewrite_count", 0) >= MAX_REWRITE_ATTEMPTS else "continue"
