from fastapi import APIRouter, HTTPException

from app.schemas.request import QueryRequest
from app.schemas.response import Citation, QueryResponse
from graph.builder import rag_graph

router = APIRouter(tags=["query"])

_INITIAL_STATE_DEFAULTS = {
    "rewritten_query": "",
    "documents": [],
    "generation": "",
    "rewrite_count": 0,
    "hallucination_score": 0.0,
    "answer_score": 0.0,
    "route_decision": "retrieve",
    "citations": [],
    "fallback": False,
}


@router.post("/{tenant_id}/query", response_model=QueryResponse)
async def query(tenant_id: str, request: QueryRequest) -> QueryResponse:
    initial_state = {
        **_INITIAL_STATE_DEFAULTS,
        "query": request.query,
        "tenant_id": tenant_id,
    }

    try:
        result = await rag_graph.ainvoke(initial_state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return QueryResponse(
        answer=result["generation"],
        confidence=round(result.get("answer_score", 0.0), 4),
        fallback=result.get("fallback", False),
        citations=[Citation(**c) for c in result.get("citations", [])],
    )
