"""Redis-backed semantic similarity cache for query responses."""
import hashlib
import json
from typing import Optional

import numpy as np

from config.constants import SEMANTIC_CACHE_SIMILARITY_THRESHOLD, SEMANTIC_CACHE_TTL_SECONDS
from observability.logging.structured_logger import get_logger

logger = get_logger(__name__)

_KEY_PREFIX = "cache"
_EMB_SUFFIX = ":emb"
_RESP_SUFFIX = ":resp"
# Index key storing all embedding hash keys for a tenant (for invalidation)
_IDX_PREFIX = "cache_idx"


def _tenant_idx_key(tenant_id: str) -> str:
    return f"{_IDX_PREFIX}:{tenant_id}"


def _query_hash(query: str) -> str:
    return hashlib.sha256(query.encode()).hexdigest()[:16]


def _emb_key(tenant_id: str, qhash: str) -> str:
    return f"{_KEY_PREFIX}:{tenant_id}:{qhash}{_EMB_SUFFIX}"


def _resp_key(tenant_id: str, qhash: str) -> str:
    return f"{_KEY_PREFIX}:{tenant_id}:{qhash}{_RESP_SUFFIX}"


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


async def _embed_query(query: str) -> list[float]:
    from llm.client import _get_embedder
    embedder = _get_embedder()
    return await embedder.aembed_query(query)


async def get(query: str, tenant_id: str, redis) -> Optional[dict]:
    """Return cached QueryResponse dict if a sufficiently similar query exists, else None."""
    if redis is None:
        return None
    try:
        query_emb = await _embed_query(query)

        # Scan all cache keys for this tenant
        idx_key = _tenant_idx_key(tenant_id)
        qhashes = await redis.smembers(idx_key)
        if not qhashes:
            return None

        for qhash in qhashes:
            raw_emb = await redis.get(_emb_key(tenant_id, qhash))
            if raw_emb is None:
                continue
            cached_emb = json.loads(raw_emb)
            sim = _cosine_similarity(query_emb, cached_emb)
            if sim >= SEMANTIC_CACHE_SIMILARITY_THRESHOLD:
                raw_resp = await redis.get(_resp_key(tenant_id, qhash))
                if raw_resp is None:
                    continue
                response = json.loads(raw_resp)
                logger.info(
                    "semantic_cache_hit",
                    tenant_id=tenant_id,
                    similarity=round(sim, 4),
                    qhash=qhash,
                )
                return response

        return None
    except Exception as exc:
        logger.warning("semantic_cache_get_failed", error=str(exc), tenant_id=tenant_id)
        return None


async def set(query: str, tenant_id: str, response: dict, redis) -> None:
    """Store query embedding + serialised response in Redis with TTL."""
    if redis is None:
        return
    try:
        query_emb = await _embed_query(query)
        qhash = _query_hash(query)

        pipe = redis.pipeline()
        pipe.set(_emb_key(tenant_id, qhash), json.dumps(query_emb), ex=SEMANTIC_CACHE_TTL_SECONDS)
        pipe.set(_resp_key(tenant_id, qhash), json.dumps(response), ex=SEMANTIC_CACHE_TTL_SECONDS)
        pipe.sadd(_tenant_idx_key(tenant_id), qhash)
        pipe.expire(_tenant_idx_key(tenant_id), SEMANTIC_CACHE_TTL_SECONDS)
        await pipe.execute()
        logger.info("semantic_cache_set", tenant_id=tenant_id, qhash=qhash)
    except Exception as exc:
        logger.warning("semantic_cache_set_failed", error=str(exc), tenant_id=tenant_id)


async def invalidate_tenant(tenant_id: str, redis) -> None:
    """Flush all cache entries for a tenant (call after doc upload/delete/replace)."""
    if redis is None:
        return
    try:
        idx_key = _tenant_idx_key(tenant_id)
        qhashes = await redis.smembers(idx_key)
        if qhashes:
            keys_to_delete = [idx_key]
            for qhash in qhashes:
                keys_to_delete.append(_emb_key(tenant_id, qhash))
                keys_to_delete.append(_resp_key(tenant_id, qhash))
            await redis.delete(*keys_to_delete)
        logger.info("semantic_cache_invalidated", tenant_id=tenant_id, entries=len(qhashes or []))
    except Exception as exc:
        logger.warning("semantic_cache_invalidate_failed", error=str(exc), tenant_id=tenant_id)
