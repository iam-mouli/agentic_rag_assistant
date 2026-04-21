from typing import List
from typing_extensions import TypedDict
from langchain_core.documents import Document


class GraphState(TypedDict):
    query: str
    rewritten_query: str
    documents: List[Document]
    generation: str
    rewrite_count: int
    hallucination_score: float
    answer_score: float
    route_decision: str
    citations: List[dict]
    fallback: bool
    tenant_id: str
