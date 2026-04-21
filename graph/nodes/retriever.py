from graph.state import GraphState
from vectorstore.retriever import retrieve_chunks
from config.constants import TOP_K_RETRIEVAL


def retriever_node(state: GraphState) -> dict:
    query = state.get("rewritten_query") or state["query"]
    documents = retrieve_chunks(query, state["tenant_id"], k=TOP_K_RETRIEVAL)
    return {"documents": documents}
