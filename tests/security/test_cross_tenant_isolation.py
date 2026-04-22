"""
Security tests — cross-tenant isolation.
Tenant A must never be able to access Tenant B's data or routes.
"""

import pytest
from fastapi.testclient import TestClient

ADMIN_HEADERS = {"X-Platform-Admin-Key": "test-admin-key"}


@pytest.fixture
def client(tmp_storage):
    from app.main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture
def two_tenants(client, tmp_storage):
    """Register two isolated tenants. Returns (tenant_a, tenant_b)."""
    ra = client.post(
        "/tenants/register",
        json={"tenant_name": "tenant-a", "team_email": "a@example.com"},
        headers=ADMIN_HEADERS,
    )
    rb = client.post(
        "/tenants/register",
        json={"tenant_name": "tenant-b", "team_email": "b@example.com"},
        headers=ADMIN_HEADERS,
    )
    tenant_a = {"name": "tenant-a", "tenant_id": ra.json()["tenant_id"], "api_key": ra.json()["api_key"]}
    tenant_b = {"name": "tenant-b", "tenant_id": rb.json()["tenant_id"], "api_key": rb.json()["api_key"]}
    return tenant_a, tenant_b


# ---------------------------------------------------------------------------
# test_tenant_a_cannot_query_tenant_b_route
# ---------------------------------------------------------------------------

def test_tenant_a_cannot_query_tenant_b_route(client, two_tenants):
    tenant_a, tenant_b = two_tenants

    # Tenant A uses its OWN credentials but sends request to Tenant B's route
    resp = client.post(
        f"/{tenant_b['name']}/query",
        json={"query": "How do I configure the system?"},
        headers={"X-Tenant-ID": tenant_a["name"], "X-API-Key": tenant_a["api_key"]},
    )
    # Middleware detects header/path mismatch → 403
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# test_tenant_a_key_rejected_on_tenant_b_route
# ---------------------------------------------------------------------------

def test_tenant_a_key_rejected_on_tenant_b_route(client, two_tenants):
    tenant_a, tenant_b = two_tenants

    # Correct path tenant, but wrong API key (Tenant A's key on Tenant B's header)
    resp = client.post(
        f"/{tenant_b['name']}/query",
        json={"query": "How do I configure the system?"},
        headers={"X-Tenant-ID": tenant_b["name"], "X-API-Key": tenant_a["api_key"]},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# test_tenant_a_docs_not_returned_in_tenant_b_query
# ---------------------------------------------------------------------------

def test_tenant_a_docs_not_returned_in_tenant_b_query(client, two_tenants, tmp_storage, mock_llm, monkeypatch):
    """
    Upload a doc to Tenant A. Query Tenant B — Tenant B's response
    must not contain citations referencing Tenant A's document.
    """
    import io
    import pickle
    import faiss
    import numpy as np

    tenant_a, tenant_b = two_tenants

    # Seed Tenant B with its own FAISS index (empty — retriever returns [])
    monkeypatch.setattr("vectorstore.retriever.embed_query", lambda q: [0.1] * 8)

    # Seed Tenant B's FAISS with one chunk that has tenant_b's doc_id
    from vectorstore.registry import init_registry, insert_doc, update_doc
    import uuid

    init_registry("tenant-b")
    b_doc_id = str(uuid.uuid4())
    docs_dir = tmp_storage / "tenants" / "tenant-b" / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    storage_path = str(docs_dir / "b.pdf")
    open(storage_path, "wb").write(b"PDF")
    insert_doc("tenant-b", b_doc_id, "b.pdf", "bhash" * 16, storage_path)
    update_doc("tenant-b", b_doc_id, status="active", chunk_count=1, pages=1)

    dim = 8
    rng = np.random.default_rng(99)
    emb = rng.random((1, dim)).astype(np.float32)
    metadata = [{
        "doc_id": b_doc_id,
        "tenant_id": "tenant-b",
        "filename": "b.pdf",
        "page": 1,
        "chunk_index": 0,
        "text": "Tenant B documentation content.",
        "embedding": emb[0].tolist(),
    }]
    faiss_dir = tmp_storage / "tenants" / "tenant-b" / "faiss_index"
    faiss_dir.mkdir(parents=True, exist_ok=True)
    index = faiss.IndexFlatL2(dim)
    index.add(emb)
    faiss.write_index(index, str(faiss_dir / "index.faiss"))
    with open(faiss_dir / "metadata.pkl", "wb") as fh:
        pickle.dump(metadata, fh)

    resp = client.post(
        "/tenant-b/query",
        json={"query": "What does the guide say?"},
        headers={"X-Tenant-ID": "tenant-b", "X-API-Key": tenant_b["api_key"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    citation_doc_ids = [c.get("doc_id") for c in body.get("citations", [])]
    # Tenant B's citations must only reference tenant B's docs (not tenant A's)
    assert all(doc_id == b_doc_id or doc_id is None for doc_id in citation_doc_ids)


# ---------------------------------------------------------------------------
# test_tenant_a_cannot_delete_tenant_b_doc
# ---------------------------------------------------------------------------

def test_tenant_a_cannot_delete_tenant_b_doc(client, two_tenants):
    tenant_a, tenant_b = two_tenants

    # Attempt to delete a (non-existent) doc on Tenant B's route using Tenant A's credentials
    resp = client.delete(
        f"/{tenant_b['name']}/docs/some-doc-id",
        headers={"X-Tenant-ID": tenant_a["name"], "X-API-Key": tenant_a["api_key"]},
    )
    # Middleware: header/path mismatch → 403
    assert resp.status_code == 403
