from arq.connections import RedisSettings

from config.constants import (
    FAISS_WRITE_LOCK_TTL_SECONDS,
    INGESTION_CHUNK_BATCH_SIZE,
    INGESTION_MAX_RETRIES,
)
from config.settings import settings
from guardrails.indirect_injection import classify_chunk
from observability.logging.structured_logger import get_logger
from vectorstore.embedder import embed_texts
from vectorstore.loader import load_and_chunk
from vectorstore.registry import update_doc
from vectorstore.store import add_chunks

logger = get_logger(__name__)


async def index_document(ctx: dict, tenant_id: str, doc_id: str, file_path: str) -> None:
    """arq job: acquire FAISS write lock → parse → chunk → embed → index → release."""
    redis = ctx.get("redis")
    lock_key = f"faiss:lock:{tenant_id}"

    if redis:
        acquired = await redis.set(lock_key, doc_id, nx=True, ex=FAISS_WRITE_LOCK_TTL_SECONDS)
        if not acquired:
            raise RuntimeError(
                f"FAISS write lock for tenant {tenant_id!r} is held — job will retry"
            )

    try:
        _ingest_sync(tenant_id, doc_id, file_path)
    finally:
        if redis:
            await redis.delete(lock_key)


def _ingest_sync(tenant_id: str, doc_id: str, file_path: str) -> None:
    """Synchronous ingestion — shared by the arq job and the dev fallback (no Redis)."""
    try:
        chunks = load_and_chunk(file_path, doc_id, tenant_id)

        safe_chunks = []
        quarantine_count = 0
        for chunk in chunks:
            if classify_chunk(chunk.page_content):
                safe_chunks.append(chunk)
            else:
                quarantine_count += 1
                logger.warning(
                    "chunk_quarantined",
                    tenant_id=tenant_id,
                    doc_id=doc_id,
                    chunk_index=chunk.metadata.get("chunk_index"),
                )

        all_embeddings: list[list[float]] = []
        for i in range(0, len(safe_chunks), INGESTION_CHUNK_BATCH_SIZE):
            batch = safe_chunks[i : i + INGESTION_CHUNK_BATCH_SIZE]
            all_embeddings.extend(embed_texts([c.page_content for c in batch]))

        add_chunks(tenant_id, safe_chunks, all_embeddings)

        pages = max((c.metadata.get("page") or 0 for c in safe_chunks), default=0)
        update_doc(
            tenant_id,
            doc_id,
            status="active",
            chunk_count=len(safe_chunks),
            pages=pages,
        )

        logger.info(
            "doc_ingested",
            tenant_id=tenant_id,
            doc_id=doc_id,
            chunk_count=len(safe_chunks),
            quarantined_count=quarantine_count,
            pages=pages,
        )

    except Exception as exc:
        update_doc(tenant_id, doc_id, status="failed", error_message=str(exc))
        logger.error(
            "ingestion_failed",
            tenant_id=tenant_id,
            doc_id=doc_id,
            error=str(exc),
        )
        raise


class WorkerSettings:
    """arq worker entry point.  Run with: arq vectorstore.ingestion_worker.WorkerSettings"""

    functions = [index_document]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 600       # seconds — large PDFs can take time to embed
    keep_result = 86400     # retain job result for 24 h
    max_tries = INGESTION_MAX_RETRIES
