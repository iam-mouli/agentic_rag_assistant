from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.history.store import clear_history, delete_query, init_history, list_history

router = APIRouter(tags=["history"])


@router.get("/{tenant_id}/history")
async def get_history(
    tenant_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> JSONResponse:
    try:
        init_history(tenant_id)
        entries = list_history(tenant_id, limit=limit, offset=offset)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse({"entries": entries, "count": len(entries)})


@router.delete("/{tenant_id}/history/{query_id}", status_code=204)
async def delete_history_entry(tenant_id: str, query_id: str) -> None:
    try:
        init_history(tenant_id)
        found = delete_query(tenant_id, query_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if not found:
        raise HTTPException(status_code=404, detail="History entry not found")


@router.delete("/{tenant_id}/history", status_code=204)
async def clear_all_history(tenant_id: str) -> None:
    try:
        init_history(tenant_id)
        clear_history(tenant_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
