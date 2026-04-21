from langgraph.graph import StateGraph, END

from graph.state import GraphState
from graph.nodes.router import router_node
from graph.nodes.retriever import retriever_node
from graph.nodes.doc_grader import doc_grader_node
from graph.nodes.query_rewriter import query_rewriter_node
from graph.nodes.generator import generator_node
from graph.nodes.hallucination_grader import hallucination_grader_node
from graph.nodes.answer_grader import answer_grader_node
from graph.edges.conditions import (
    route_query,
    check_direct_answer,
    grade_documents,
    check_hallucination,
    check_answer,
    check_loop_limit,
)
from observability.graph_tracing import traced_node

_FALLBACK_ANSWER = (
    "I wasn't able to find a reliable answer in the documentation. "
    "Please refer to the source docs or contact your SME."
)


def _fallback_node(state: GraphState) -> dict:
    return {
        "generation": _FALLBACK_ANSWER,
        "hallucination_score": 0.0,
        "answer_score": 0.0,
        "citations": [],
        "fallback": True,
    }


def build_graph():
    workflow = StateGraph(GraphState)

    workflow.add_node("router", traced_node("router", router_node))
    workflow.add_node("retriever", traced_node("retriever", retriever_node))
    workflow.add_node("doc_grader", traced_node("doc_grader", doc_grader_node))
    workflow.add_node("query_rewriter", traced_node("query_rewriter", query_rewriter_node))
    workflow.add_node("generator", traced_node("generator", generator_node))
    workflow.add_node("hallucination_grader", traced_node("hallucination_grader", hallucination_grader_node))
    workflow.add_node("answer_grader", traced_node("answer_grader", answer_grader_node))
    workflow.add_node("fallback", traced_node("fallback", _fallback_node))

    workflow.set_entry_point("router")

    # Router → retrieve path or direct-answer path
    workflow.add_conditional_edges(
        "router",
        route_query,
        {"retrieve": "retriever", "direct_answer": "generator"},
    )

    workflow.add_edge("retriever", "doc_grader")

    # DocGrader → generate (if relevant docs) or rewrite
    workflow.add_conditional_edges(
        "doc_grader",
        grade_documents,
        {"generate": "generator", "rewrite_query": "query_rewriter"},
    )

    # Generator → skip graders for direct-answer, enter grader chain for retrieve
    workflow.add_conditional_edges(
        "generator",
        check_direct_answer,
        {"end": END, "grade": "hallucination_grader"},
    )

    # HallucinationGrader → answer grader (grounded) or rewrite (not grounded)
    workflow.add_conditional_edges(
        "hallucination_grader",
        check_hallucination,
        {"grounded": "answer_grader", "not_grounded": "query_rewriter"},
    )

    # AnswerGrader → done (useful) or rewrite (not useful)
    workflow.add_conditional_edges(
        "answer_grader",
        check_answer,
        {"useful": END, "not_useful": "query_rewriter"},
    )

    # QueryRewriter → retriever (continue) or fallback (loop limit reached)
    workflow.add_conditional_edges(
        "query_rewriter",
        check_loop_limit,
        {"continue": "retriever", "fallback": "fallback"},
    )

    workflow.add_edge("fallback", END)

    return workflow.compile()


# Module-level compiled graph — import this in routes
rag_graph = build_graph()
