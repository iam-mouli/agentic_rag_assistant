from fastapi import APIRouter, HTTPException

from app.schemas.request import QueryRequest
from app.schemas.response import Citation, QueryResponse
from graph.builder import rag_graph
from guardrails import run_input_guardrails, run_output_guardrails
from guardrails.output.confidence_tagger import tag_confidence

router = APIRouter(tags=["query"])


def _build_initial_state(query: str, tenant_id: str) -> dict:
    return {
        "query": query,
        "tenant_id": tenant_id,
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
    input_guard = run_input_guardrails(request.query)
    if not input_guard.passed:
        raise HTTPException(
            status_code=422,
            detail={"code": input_guard.block_code, "reason": input_guard.reason},
        )

    initial_state = _build_initial_state(request.query, tenant_id)

    try:
        result = await rag_graph.ainvoke(initial_state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    output_guard = run_output_guardrails(result)
    if not output_guard.passed:
        raise HTTPException(
            status_code=422,
            detail={"code": output_guard.block_code, "reason": output_guard.reason},
        )

    answer_score = round(result.get("answer_score", 0.0), 4)
    return QueryResponse(
        answer=result["generation"],
        confidence=answer_score,
        confidence_level=tag_confidence(answer_score),
        fallback=result.get("fallback", False),
        citations=[Citation(**c) for c in result.get("citations", [])],
    )
