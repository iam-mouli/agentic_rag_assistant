import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from config.settings import settings
from observability import semantic_cache
from vectorstore.loader import compute_file_hash
from vectorstore.registry import (
    get_doc,
    get_doc_by_hash,
    init_registry,
    insert_doc,
    list_docs,
    update_doc,
)
from vectorstore.store import remove_doc_chunks

router = APIRouter(tags=["docs"])


def _docs_dir(tenant_id: str) -> Path:
    return Path(settings.STORAGE_BASE_PATH) / "tenants" / tenant_id / "docs"


async def _enqueue_or_ingest(
    request: Request, tenant_id: str, doc_id: str, file_path: str
) -> None:
    arq_pool = getattr(request.app.state, "arq_pool", None)
    if arq_pool:
        await arq_pool.enqueue_job("index_document", tenant_id, doc_id, file_path)
    else:
        # Dev fallback: ingest synchronously when arq worker is not running
        from vectorstore.ingestion_worker import _ingest_sync
        _ingest_sync(tenant_id, doc_id, file_path)


@router.post("/{tenant_id}/docs/upload", status_code=202)
async def upload_doc(tenant_id: str, request: Request, file: UploadFile = File(...)):
    init_registry(tenant_id)
    docs_dir = _docs_dir(tenant_id)
    docs_dir.mkdir(parents=True, exist_ok=True)

    temp_path = docs_dir / f"_tmp_{uuid.uuid4()}_{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        file_hash = compute_file_hash(str(temp_path))
        duplicate = get_doc_by_hash(tenant_id, file_hash)
        if duplicate:
            raise HTTPException(
                status_code=409,
                detail=f"Document already indexed as doc_id={duplicate['doc_id']}",
            )

        doc_id = str(uuid.uuid4())
        final_path = docs_dir / f"{doc_id}_{file.filename}"
        temp_path.rename(final_path)

    except HTTPException:
        temp_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    insert_doc(tenant_id, doc_id, file.filename, file_hash, str(final_path))
    await _enqueue_or_ingest(request, tenant_id, doc_id, str(final_path))
    await semantic_cache.invalidate_tenant(tenant_id, getattr(request.app.state, "redis", None))

    return {"doc_id": doc_id, "filename": file.filename, "status": "processing"}


@router.get("/{tenant_id}/docs")
async def list_docs_route(tenant_id: str):
    init_registry(tenant_id)
    docs = list_docs(tenant_id)
    total_chunks = sum(d.get("chunk_count") or 0 for d in docs)
    return {
        "tenant_id": tenant_id,
        "total_docs": len(docs),
        "total_chunks": total_chunks,
        "documents": docs,
    }


@router.get("/{tenant_id}/docs/{doc_id}")
async def get_doc_route(tenant_id: str, doc_id: str):
    init_registry(tenant_id)
    doc = get_doc(tenant_id, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{tenant_id}/docs/{doc_id}")
async def delete_doc(tenant_id: str, doc_id: str, request: Request):
    init_registry(tenant_id)
    doc = get_doc(tenant_id, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc["status"] == "removed":
        raise HTTPException(status_code=409, detail="Document already removed")

    chunks_removed = remove_doc_chunks(tenant_id, doc_id)
    update_doc(tenant_id, doc_id, status="removed")
    await semantic_cache.invalidate_tenant(tenant_id, getattr(request.app.state, "redis", None))

    return {"doc_id": doc_id, "status": "removed", "chunks_removed": chunks_removed}


@router.put("/{tenant_id}/docs/{doc_id}")
async def update_doc_route(tenant_id: str, doc_id: str, request: Request, file: UploadFile = File(...)):
    init_registry(tenant_id)
    existing = get_doc(tenant_id, doc_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Document not found")
    if existing["status"] in ("removed", "superseded"):
        raise HTTPException(status_code=409, detail="Cannot update a removed or superseded document")

    docs_dir = _docs_dir(tenant_id)
    temp_path = docs_dir / f"_tmp_{uuid.uuid4()}_{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        file_hash = compute_file_hash(str(temp_path))
        new_doc_id = str(uuid.uuid4())
        final_path = docs_dir / f"{new_doc_id}_{file.filename}"
        temp_path.rename(final_path)

    except Exception as exc:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # Retire old version
    update_doc(tenant_id, doc_id, status="superseded")
    remove_doc_chunks(tenant_id, doc_id)

    # Bump version number
    old_version = existing.get("version") or "v1"
    try:
        new_version = f"v{int(old_version.lstrip('v')) + 1}"
    except (ValueError, AttributeError):
        new_version = f"{old_version}-updated"

    insert_doc(tenant_id, new_doc_id, file.filename, file_hash, str(final_path), version=new_version)
    await _enqueue_or_ingest(request, tenant_id, new_doc_id, str(final_path))
    await semantic_cache.invalidate_tenant(tenant_id, getattr(request.app.state, "redis", None))

    return {
        "old_doc_id": doc_id,
        "new_doc_id": new_doc_id,
        "old_version": old_version,
        "new_version": new_version,
        "status": "processing",
    }
