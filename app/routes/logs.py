from typing import Any, Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from config.settings import settings
from observability.logging.file_handler import read_logs
from vectorstore.registry import init_registry, list_docs

router = APIRouter(tags=["logs"])


# ---------------------------------------------------------------------------
# Tab 1: Application logs (structlog → JSONL file)
# ---------------------------------------------------------------------------

@router.get("/{tenant_id}/logs/app")
async def get_app_logs(
    tenant_id: str,
    level: Optional[str] = Query(None, description="Filter by log level (info, warning, error)"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
) -> JSONResponse:
    entries = read_logs(tenant_id=tenant_id, level=level, limit=limit, offset=offset)
    return JSONResponse({"entries": entries, "count": len(entries)})


# ---------------------------------------------------------------------------
# Tab 2: LangSmith traces (proxied server-side so API key stays hidden)
# ---------------------------------------------------------------------------

def _serialize_run(run: Any) -> dict:
    """Convert a LangSmith Run object to a JSON-serialisable dict."""
    start = run.start_time.isoformat() if run.start_time else None
    end = run.end_time.isoformat() if run.end_time else None
    latency_ms = None
    if run.start_time and run.end_time:
        latency_ms = round((run.end_time - run.start_time).total_seconds() * 1000, 1)

    metadata: dict = {}
    if run.extra:
        metadata = run.extra.get("metadata", {})

    return {
        "run_id": str(run.id),
        "start_time": start,
        "end_time": end,
        "latency_ms": latency_ms,
        "status": run.status,
        "inputs": run.inputs or {},
        "outputs": run.outputs or {},
        "error": run.error,
        "metadata": metadata,
    }


@router.get("/{tenant_id}/logs/traces")
async def get_traces(
    tenant_id: str,
    limit: int = Query(20, le=100),
) -> JSONResponse:
    if not settings.LANGSMITH_API_KEY:
        return JSONResponse({"runs": [], "langsmith_enabled": False})

    try:
        from langsmith import Client

        client = Client(api_key=settings.LANGSMITH_API_KEY)
        # Fetch recent runs and filter by tenant in Python — simpler than filter syntax.
        raw_runs = list(
            client.list_runs(
                project_name=settings.LANGSMITH_PROJECT,
                run_type="chain",
                limit=limit * 5,  # over-fetch to account for cross-tenant runs
            )
        )
        tenant_runs = [
            r for r in raw_runs
            if (r.extra or {}).get("metadata", {}).get("tenant_id") == tenant_id
        ][:limit]

        return JSONResponse({
            "runs": [_serialize_run(r) for r in tenant_runs],
            "langsmith_enabled": True,
        })
    except Exception as exc:
        return JSONResponse({"runs": [], "langsmith_enabled": True, "error": str(exc)})


# ---------------------------------------------------------------------------
# Tab 3: Ingestion jobs (doc registry)
# ---------------------------------------------------------------------------

@router.get("/{tenant_id}/logs/ingestion")
async def get_ingestion_logs(
    tenant_id: str,
    status: Optional[str] = Query(None, description="Filter by status (failed, active, processing…)"),
    limit: int = Query(50, le=200),
) -> JSONResponse:
    try:
        init_registry(tenant_id)
        docs = list_docs(tenant_id)
    except Exception as exc:
        return JSONResponse({"jobs": [], "error": str(exc)})

    if status:
        docs = [d for d in docs if d.get("status") == status]

    jobs = [
        {
            "doc_id": d["doc_id"],
            "filename": d["filename"],
            "status": d["status"],
            "uploaded_at": d.get("upload_date"),
            "chunk_count": d.get("chunk_count"),
            "pages": d.get("pages"),
            "error_message": d.get("error_message"),
        }
        for d in docs[:limit]
    ]
    return JSONResponse({"jobs": jobs, "count": len(jobs)})
