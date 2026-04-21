from graph.state import GraphState
from llm.openai_client import grade
from prompts.hallucination_grader_prompt import build_hallucination_messages


def hallucination_grader_node(state: GraphState) -> dict:
    messages = build_hallucination_messages(state["generation"], state.get("documents", []))
    response, _ = grade(messages)
    try:
        score = float(response.strip())
    except ValueError:
        score = 0.0 if "no" in response.lower() else 1.0
    return {"hallucination_score": score}
