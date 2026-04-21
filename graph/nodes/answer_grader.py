from graph.state import GraphState
from llm.client import grade
from prompts.answer_grader_prompt import build_answer_grader_messages


def answer_grader_node(state: GraphState) -> dict:
    messages = build_answer_grader_messages(state["query"], state["generation"])
    response, _ = grade(messages)
    try:
        score = float(response.strip())
    except ValueError:
        score = 0.0 if "no" in response.lower() else 1.0
    return {"answer_score": score}
