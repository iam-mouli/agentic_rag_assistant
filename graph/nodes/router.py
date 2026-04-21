from graph.state import GraphState
from llm.openai_client import grade
from prompts.router_prompt import build_router_messages


def router_node(state: GraphState) -> dict:
    messages = build_router_messages(state["query"])
    response, _ = grade(messages)
    decision = "direct_answer" if "direct_answer" in response.lower() else "retrieve"
    return {"route_decision": decision}
