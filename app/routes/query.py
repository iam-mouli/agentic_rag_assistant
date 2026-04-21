import time
import uuid

import structlog
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.schemas.request import QueryRequest
from app.schemas.response import Citation, QueryResponse
from graph.builder import rag_graph
from guardrails import run_input_guardrails, run_output_guardrails
from guardrails.output.confidence_tagger import tag_confidence
from observability.langsmith.tracer import get_run_id, populate_carrier, trace_graph_run
from observability.logging.structured_logger import get_logger

router = APIRouter(tags=["query"])
logger = get_logger(__name__)


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


@router.post("/{tenant_id}/query")
async def query(tenant_id: str, request: QueryRequest, http_request: Request) -> JSONResponse:
    request_id = str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id, tenant_id=tenant_id)

    t0 = time.monotonic()

    input_guard = run_input_guardrails(request.query)
    if not input_guard.passed:
        logger.warning(
            "guardrail_input_block",
            block_code=input_guard.block_code,
            reason=input_guard.reason,
            query_excerpt=request.query[:80],
            latency_ms=round((time.monotonic() - t0) * 1000, 1),
        )
        raise HTTPException(
            status_code=422,
            detail={"code": input_guard.block_code, "reason": input_guard.reason},
        )

    initial_state = _build_initial_state(request.query, tenant_id)

    async with trace_graph_run(tenant_id=tenant_id, query=request.query) as carrier:
        try:
            result = await rag_graph.ainvoke(initial_state)
        except Exception as exc:
            logger.error(
                "graph_invocation_failed",
                error=str(exc),
                latency_ms=round((time.monotonic() - t0) * 1000, 1),
            )
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        populate_carrier(carrier, result)

        output_guard = run_output_guardrails(result)
        if not output_guard.passed:
            logger.warning(
                "guardrail_output_block",
                block_code=output_guard.block_code,
                reason=output_guard.reason,
                query_excerpt=request.query[:80],
                latency_ms=round((time.monotonic() - t0) * 1000, 1),
            )
            raise HTTPException(
                status_code=422,
                detail={"code": output_guard.block_code, "reason": output_guard.reason},
            )

        latency_ms = round((time.monotonic() - t0) * 1000, 1)
        logger.info(
            "query_completed",
            route_decision=result.get("route_decision"),
            rewrite_count=result.get("rewrite_count", 0),
            hallucination_score=result.get("hallucination_score"),
            answer_score=result.get("answer_score"),
            fallback=result.get("fallback", False),
            latency_ms=latency_ms,
        )

        answer_score = round(result.get("answer_score", 0.0), 4)
        response_body = QueryResponse(
            answer=result["generation"],
            confidence=answer_score,
            confidence_level=tag_confidence(answer_score),
            fallback=result.get("fallback", False),
            citations=[Citation(**c) for c in result.get("citations", [])],
        )

    run_id = get_run_id(carrier)
    headers = {"X-Run-ID": run_id} if run_id else {}
    return JSONResponse(
        content=response_body.model_dump(),
        headers=headers,
    )
