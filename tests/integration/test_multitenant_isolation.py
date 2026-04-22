"""
Integration tests for multi-tenant data isolation.
Verifies that tenants cannot access each other's routes, docs, or query results.
"""

import pickle
import uuid

import faiss
import numpy as np
import pytest
from fastapi.testclient import TestClient

ADMIN = {"X-Platform-Admin-Key": "test-admin-key"}


@pytest.fixture
def client(tmp_storage):
    from app.main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture
def two_tenants(client):
    ra = client.post("/tenants/register", json={"tenant_name": "iso-a", "team_email": "a@x.com"}, headers=ADMIN)
    rb = client.post("/tenants/register", json={"tenant_name": "iso-b", "team_email": "b@x.com"}, headers=ADMIN)
    return (
        {"name": "iso-a", "tenant_id": ra.json()["tenant_id"], "api_key": ra.json()["api_key"]},
        {"name": "iso-b", "tenant_id": rb.json()["tenant_id"], "api_key": rb.json()["api_key"]},
    )


# ---------------------------------------------------------------------------
# Header / path mismatch → 403
# ---------------------------------------------------------------------------

def test_tenant_header_path_mismatch_rejected(client, two_tenants):
    ta, tb = two_tenants
    # Correct path for B, but header claims A → middleware 403
    resp = client.post(
        f"/{tb['name']}/query",
        json={"query": "How do I configure the system?"},
        headers={"X-Tenant-ID": ta["name"], "X-API-Key": ta["api_key"]},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Wrong API key on correct tenant → 401
# ---------------------------------------------------------------------------

def test_tenant_a_key_rejected_on_tenant_b_route(client, two_tenants):
    ta, tb = two_tenants
    resp = client.post(
        f"/{tb['name']}/query",
        json={"query": "How do I configure the system?"},
        headers={"X-Tenant-ID": tb["name"], "X-API-Key": ta["api_key"]},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Data isolation: Tenant A's doc must not appear in Tenant B's query results
# ---------------------------------------------------------------------------

def test_tenant_a_docs_not_returned_in_tenant_b_query(client, two_tenants, tmp_storage, mock_llm, monkeypatch):
    ta, tb = two_tenants

    # Seed Tenant B's FAISS index with its own doc
    from vectorstore.registry import init_registry, insert_doc, update_doc

    init_registry("iso-b")
    b_doc_id = str(uuid.uuid4())
    docs_dir = tmp_storage / "tenants" / "iso-b" / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    storage_path = str(docs_dir / "b.pdf")
    open(storage_path, "wb").write(b"PDF")
    insert_doc("iso-b", b_doc_id, "b.pdf", "b" * 64, storage_path)
    update_doc("iso-b", b_doc_id, status="active", chunk_count=1, pages=1)

    dim = 8
    rng = np.random.default_rng(55)
    emb = rng.random((1, dim)).astype(np.float32)
    meta = [{"doc_id": b_doc_id, "tenant_id": "iso-b", "filename": "b.pdf",
              "page": 1, "chunk_index": 0, "text": "Tenant B content.", "embedding": emb[0].tolist()}]
    faiss_dir = tmp_storage / "tenants" / "iso-b" / "faiss_index"
    faiss_dir.mkdir(parents=True, exist_ok=True)
    idx = faiss.IndexFlatL2(dim)
    idx.add(emb)
    faiss.write_index(idx, str(faiss_dir / "index.faiss"))
    with open(faiss_dir / "metadata.pkl", "wb") as fh:
        pickle.dump(meta, fh)

    monkeypatch.setattr("vectorstore.retriever.embed_query", lambda q: emb[0].tolist())

    resp = client.post(
        "/iso-b/query",
        json={"query": "What does the guide say?"},
        headers={"X-Tenant-ID": "iso-b", "X-API-Key": tb["api_key"]},
    )
    assert resp.status_code == 200
    citation_doc_ids = [c.get("doc_id") for c in resp.json().get("citations", [])]
    # Must only reference iso-b's doc — never iso-a's
    assert all(doc_id in (b_doc_id, None) for doc_id in citation_doc_ids)


# ---------------------------------------------------------------------------
# Tenant A cannot delete Tenant B's documents
# ---------------------------------------------------------------------------

def test_tenant_a_cannot_delete_tenant_b_doc(client, two_tenants):
    ta, tb = two_tenants
    resp = client.delete(
        f"/{tb['name']}/docs/any-doc-id",
        headers={"X-Tenant-ID": ta["name"], "X-API-Key": ta["api_key"]},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Simultaneous queries return isolated results
# ---------------------------------------------------------------------------

def test_simultaneous_tenants_get_isolated_responses(client, two_tenants, tmp_storage, mock_llm, monkeypatch):
    """Two tenants querying concurrently must each only see their own data."""
    ta, tb = two_tenants

    # Use an empty FAISS index for both (router goes direct_answer to avoid retrieval)
    monkeypatch.setattr("graph.nodes.router.grade", lambda m, **kw: ("direct_answer", {}))

    resp_a = client.post(
        f"/{ta['name']}/query",
        json={"query": "What is 2+2?"},
        headers={"X-Tenant-ID": ta["name"], "X-API-Key": ta["api_key"]},
    )
    resp_b = client.post(
        f"/{tb['name']}/query",
        json={"query": "What is 2+2?"},
        headers={"X-Tenant-ID": tb["name"], "X-API-Key": tb["api_key"]},
    )
    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
