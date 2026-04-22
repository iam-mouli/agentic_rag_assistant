"""Unit tests for semantic cache module. Redis calls use AsyncMock."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from config.constants import SEMANTIC_CACHE_SIMILARITY_THRESHOLD
from observability import semantic_cache


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_async_redis(store: dict | None = None):
    """Build an AsyncMock that simulates a minimal Redis interface."""
    if store is None:
        store = {}

    redis = AsyncMock()

    async def fake_smembers(key):
        return store.get(key, set())

    async def fake_get(key):
        val = store.get(key)
        return json.dumps(val) if val is not None else None

    async def fake_set(key, value, ex=None):
        store[key] = json.loads(value)

    async def fake_sadd(key, *values):
        existing = store.get(key, set())
        existing.update(values)
        store[key] = existing

    async def fake_delete(*keys):
        for k in keys:
            store.pop(k, None)

    redis.smembers.side_effect = fake_smembers
    redis.get.side_effect = fake_get
    redis.set.side_effect = fake_set
    redis.sadd.side_effect = fake_sadd
    redis.delete.side_effect = fake_delete

    # Pipeline mock
    pipe = AsyncMock()
    pipe.__aenter__ = AsyncMock(return_value=pipe)
    pipe.__aexit__ = AsyncMock(return_value=False)
    pipe.set = MagicMock(return_value=pipe)
    pipe.sadd = MagicMock(return_value=pipe)
    pipe.expire = MagicMock(return_value=pipe)
    pipe.execute = AsyncMock(return_value=[True, True, 1, True])

    redis.pipeline.return_value = pipe

    return redis, store


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cache_miss_returns_none():
    redis, _ = _make_async_redis()

    async def fake_embed(q):
        return [0.1] * 8

    with patch("observability.semantic_cache._embed_query", fake_embed):
        result = await semantic_cache.get("How to configure alerts?", "tenant-a", redis)

    assert result is None


@pytest.mark.asyncio
async def test_cache_set_and_get_returns_response():
    store: dict = {}
    redis, store = _make_async_redis(store)

    emb = [0.9] * 8
    response = {"answer": "Configure via Settings menu.", "confidence": 0.88, "fallback": False}

    async def fake_embed(q):
        return emb

    with patch("observability.semantic_cache._embed_query", fake_embed):
        await semantic_cache.set("How to configure alerts?", "tenant-a", response, redis)
        result = await semantic_cache.get("How to configure alerts?", "tenant-a", redis)

    assert result is not None
    assert result["answer"] == response["answer"]


@pytest.mark.asyncio
async def test_cache_hit_requires_similarity_above_threshold():
    """Two identical embeddings → cosine similarity 1.0 → cache hit."""
    store: dict = {}
    redis, store = _make_async_redis(store)
    emb = [0.5, 0.5, 0.5, 0.5, 0.0, 0.0, 0.0, 0.0]
    response = {"answer": "Answer A", "confidence": 0.9, "fallback": False}

    async def same_embed(q):
        return emb

    with patch("observability.semantic_cache._embed_query", same_embed):
        await semantic_cache.set("query", "tenant-a", response, redis)
        result = await semantic_cache.get("query", "tenant-a", redis)

    assert result is not None


@pytest.mark.asyncio
async def test_cache_miss_below_threshold():
    """Orthogonal embeddings → cosine similarity 0.0 → cache miss."""
    store: dict = {}
    redis, store = _make_async_redis(store)

    emb_stored = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    emb_query = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    response = {"answer": "Some answer", "confidence": 0.8, "fallback": False}

    call_count = 0

    async def alternating_embed(q):
        nonlocal call_count
        call_count += 1
        return emb_stored if call_count == 1 else emb_query

    with patch("observability.semantic_cache._embed_query", alternating_embed):
        await semantic_cache.set("original query", "tenant-a", response, redis)
        result = await semantic_cache.get("completely different query", "tenant-a", redis)

    assert result is None


@pytest.mark.asyncio
async def test_invalidate_tenant_flushes_all_keys():
    store: dict = {}
    redis, store = _make_async_redis(store)
    emb = [0.5] * 8
    response = {"answer": "Cached", "confidence": 0.9, "fallback": False}

    async def fake_embed(q):
        return emb

    with patch("observability.semantic_cache._embed_query", fake_embed):
        await semantic_cache.set("query one", "tenant-a", response, redis)
        await semantic_cache.invalidate_tenant("tenant-a", redis)
        result = await semantic_cache.get("query one", "tenant-a", redis)

    assert result is None


@pytest.mark.asyncio
async def test_cache_fails_open_when_redis_unavailable():
    """None redis → get returns None, set returns None — no exception raised."""
    result = await semantic_cache.get("any query", "tenant-x", None)
    assert result is None

    await semantic_cache.set("any query", "tenant-x", {"answer": "x"}, None)
