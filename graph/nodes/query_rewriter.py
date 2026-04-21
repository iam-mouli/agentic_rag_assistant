from graph.state import GraphState
from llm.openai_client import grade
from prompts.query_rewriter_prompt import build_rewriter_messages


def query_rewriter_node(state: GraphState) -> dict:
    messages = build_rewriter_messages(state["query"])
    response, _ = grade(messages)
    return {
        "rewritten_query": response.strip(),
        "rewrite_count": state.get("rewrite_count", 0) + 1,
    }
