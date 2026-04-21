from graph.state import GraphState
from llm.openai_client import grade
from prompts.doc_grader_prompt import build_doc_grader_messages


def doc_grader_node(state: GraphState) -> dict:
    query = state.get("rewritten_query") or state["query"]
    graded = []
    for doc in state.get("documents", []):
        messages = build_doc_grader_messages(query, doc.page_content)
        response, _ = grade(messages)
        if "yes" in response.lower():
            graded.append(doc)
    return {"documents": graded}
