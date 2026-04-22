"""
Shared fixtures for all test layers (unit, integration, security).

Fixture hierarchy:
  tmp_storage         — monkeypatches settings to use a temp dir
  real_db             — real SQLite tenants.db in tmp_storage
  registered_tenant   — one real tenant registered in real_db
  tenant_client       — TestClient + tenant headers (depends on registered_tenant)
  seeded_tenant       — registered_tenant + one pre-indexed test doc + mock embed
  mock_llm            — patches all LLM calls with deterministic responses
  mock_redis          — async-compatible in-memory Redis (fakeredis)
"""

import pickle
import uuid
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document


# ---------------------------------------------------------------------------
# Storage isolation
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_storage(tmp_path, monkeypatch):
    """Redirect all file I/O to a temp directory. Monkeypatches settings."""
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()

    from config.settings import settings
    monkeypatch.setattr(settings, "STORAGE_BASE_PATH", str(storage_dir))
    monkeypatch.setattr(settings, "MASTER_DB_PATH", str(storage_dir / "tenants.db"))
    monkeypatch.setattr(settings, "PLATFORM_ADMIN_KEY", "test-admin-key")

    return storage_dir


# ---------------------------------------------------------------------------
# Real SQLite database
# ---------------------------------------------------------------------------

@pytest.fixture
def real_db(tmp_storage):
    """Initialize real tenants.db in tmp_storage. Returns path."""
    from tenants.registry import init_db
    init_db()
    return tmp_storage / "tenants.db"


# ---------------------------------------------------------------------------
# Registered tenant
# ---------------------------------------------------------------------------

@pytest.fixture
def registered_tenant(real_db, tmp_storage):
    """Register a test tenant in the real DB. Returns name, tenant_id, api_key."""
    from tenants.manager import register_tenant
    result = register_tenant("test-tenant", "test@example.com")
    return {
        "name": "test-tenant",
        "tenant_id": result["tenant_id"],
        "api_key": result["api_key"],
    }


# ---------------------------------------------------------------------------
# TestClient + tenant headers
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant_client(registered_tenant, tmp_storage):
    """
    TestClient for the FastAPI app with the registered test tenant.
    Yields (client, tenant_info). Use tenant_info for per-request headers.
    """
    from app.main import app
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client, registered_tenant


# ---------------------------------------------------------------------------
# LLM mock — patches all node-level grade/generate calls
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm(monkeypatch):
    """
    Replace LLM calls in every graph node with deterministic responses:
      router      → "retrieve"
      doc_grader  → "yes" (all chunks pass)
      rewriter    → a rephrased query string
      hallucination_grader → "0.90" (well above threshold)
      answer_grader        → "0.90" (well above threshold)
      generator   → a canned answer
    """

    def _grade_retrieve(messages, **kwargs):
        return "retrieve", {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10, "model": "mock"}

    def _grade_yes(messages, **kwargs):
        return "yes", {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10, "model": "mock"}

    def _grade_score(messages, **kwargs):
        return "0.90", {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10, "model": "mock"}

    def _grade_rewrite(messages, **kwargs):
        return "How is configuration done in detail?", {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15, "model": "mock"}

    def _generate(messages, **kwargs):
        return "Mock generated answer about configuration.", {
            "prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30, "model": "mock"
        }

    monkeypatch.setattr("graph.nodes.router.grade", _grade_retrieve)
    monkeypatch.setattr("graph.nodes.doc_grader.grade", _grade_yes)
    monkeypatch.setattr("graph.nodes.query_rewriter.grade", _grade_rewrite)
    monkeypatch.setattr("graph.nodes.hallucination_grader.grade", _grade_score)
    monkeypatch.setattr("graph.nodes.answer_grader.grade", _grade_score)
    monkeypatch.setattr("graph.nodes.generator.generate", _generate)

    return {
        "router": _grade_retrieve,
        "doc_grader": _grade_yes,
        "rewriter": _grade_rewrite,
        "hallucination": _grade_score,
        "answer": _grade_score,
        "generate": _generate,
    }


# ---------------------------------------------------------------------------
# Redis mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_redis():
    """In-memory Redis using fakeredis. Skips test if fakeredis is not installed."""
    fakeredis = pytest.importorskip("fakeredis", reason="fakeredis not installed — pip install fakeredis")
    return fakeredis.FakeRedis(decode_responses=True)


# ---------------------------------------------------------------------------
# Seeded tenant — registered tenant + pre-indexed test doc
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded_tenant(registered_tenant, tmp_storage, monkeypatch):
    """
    Extends registered_tenant with one pre-indexed test document.

    Creates:
      - real doc registry entry (status=active, chunk_count=3)
      - real FAISS index (dim=8, 3 chunks)

    Monkeypatches vectorstore.retriever.embed_query to return
    a fixed 8-dim vector compatible with the test index.
    """
    import faiss
    from vectorstore.registry import init_registry, insert_doc, update_doc

    tenant_name = registered_tenant["name"]
    dim = 8

    init_registry(tenant_name)

    doc_id = str(uuid.uuid4())
    file_hash = "a" * 64

    docs_dir = tmp_storage / "tenants" / tenant_name / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    storage_path = str(docs_dir / "test.pdf")
    Path(storage_path).write_bytes(b"%PDF-1.4 test")

    insert_doc(tenant_name, doc_id, "test.pdf", file_hash, storage_path)
    update_doc(tenant_name, doc_id, status="active", chunk_count=3, pages=1)

    rng = np.random.default_rng(42)
    embeddings = rng.random((3, dim)).astype(np.float32)

    metadata = [
        {
            "doc_id": doc_id,
            "tenant_id": tenant_name,
            "filename": "test.pdf",
            "page": 1,
            "chunk_index": i,
            "text": f"Chunk {i}: configuration steps for the system.",
            "embedding": embeddings[i].tolist(),
        }
        for i in range(3)
    ]

    faiss_dir = tmp_storage / "tenants" / tenant_name / "faiss_index"
    faiss_dir.mkdir(parents=True, exist_ok=True)
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    faiss.write_index(index, str(faiss_dir / "index.faiss"))
    with open(faiss_dir / "metadata.pkl", "wb") as fh:
        pickle.dump(metadata, fh)

    query_vec = rng.random(dim).astype(np.float32).tolist()
    monkeypatch.setattr("vectorstore.retriever.embed_query", lambda q: query_vec)

    return {
        **registered_tenant,
        "doc_id": doc_id,
        "file_hash": file_hash,
        "dim": dim,
    }
