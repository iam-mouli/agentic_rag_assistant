from graph.state import GraphState
from llm.openai_client import generate
from prompts.generator_prompt import build_generator_messages


def generator_node(state: GraphState) -> dict:
    query = state.get("rewritten_query") or state["query"]
    documents = state.get("documents", [])
    is_direct = state.get("route_decision") == "direct_answer"

    messages = build_generator_messages(query, documents, direct=is_direct)
    response, _ = generate(messages)

    citations = [
        {
            "doc_id": doc.metadata.get("doc_id"),
            "filename": doc.metadata.get("filename"),
            "page": doc.metadata.get("page"),
            "chunk_preview": doc.page_content[:200],
        }
        for doc in documents
        if doc.metadata.get("doc_id")
    ]

    return {"generation": response, "citations": citations}
