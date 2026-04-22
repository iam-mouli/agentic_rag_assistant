"""
Integration tests for the full tenant onboarding lifecycle.
Register → upload doc → query → verify citation from uploaded doc.
Real SQLite. LLM mocked.
"""

import io

import pytest
from fastapi.testclient import TestClient

from tenants.auth import verify_api_key
from tenants.registry import get_tenant_by_id

ADMIN = {"X-Platform-Admin-Key": "test-admin-key"}


@pytest.fixture
def client(tmp_storage):
    from app.main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture
def mock_ingest(monkeypatch):
    def _stub(tid, did, fp):
        from vectorstore.registry import update_doc
        update_doc(tid, did, status="active", chunk_count=3, pages=1)
    monkeypatch.setattr("vectorstore.ingestion_worker._ingest_sync", _stub)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def test_register_tenant_creates_storage_structure(client, tmp_storage):
    resp = client.post(
        "/tenants/register",
        json={"tenant_name": "onboard-team", "team_email": "t@example.com"},
        headers=ADMIN,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "tenant_id" in body
    assert "api_key" in body
    assert (tmp_storage / "tenants" / "onboard-team" / "docs").is_dir()
    assert (tmp_storage / "tenants" / "onboard-team" / "faiss_index").is_dir()


def test_duplicate_tenant_name_rejected(client):
    payload = {"tenant_name": "dup-team", "team_email": "d@example.com"}
    r1 = client.post("/tenants/register", json=payload, headers=ADMIN)
    assert r1.status_code == 201
    r2 = client.post("/tenants/register", json=payload, headers=ADMIN)
    assert r2.status_code == 400


# ---------------------------------------------------------------------------
# Deactivation
# ---------------------------------------------------------------------------

def test_deactivated_tenant_rejected_on_query(client, registered_tenant):
    tenant_id = registered_tenant["tenant_id"]
    name = registered_tenant["name"]
    api_key = registered_tenant["api_key"]

    client.delete(f"/tenants/{tenant_id}", headers=ADMIN)

    resp = client.post(
        f"/{name}/query",
        json={"query": "How do I configure the system?"},
        headers={"X-Tenant-ID": name, "X-API-Key": api_key},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Key rotation
# ---------------------------------------------------------------------------

def test_rotate_key_old_key_rejected_new_key_accepted(client, registered_tenant):
    tenant_id = registered_tenant["tenant_id"]
    old_key = registered_tenant["api_key"]

    rotate = client.post(f"/tenants/{tenant_id}/rotate-key", headers=ADMIN)
    assert rotate.status_code == 200
    new_key = rotate.json()["api_key"]

    tenant = get_tenant_by_id(tenant_id)
    assert verify_api_key(old_key, tenant["api_key_hash"]) is False
    assert verify_api_key(new_key, tenant["api_key_hash"]) is True


# ---------------------------------------------------------------------------
# End-to-end: register → upload → query → citation
# ---------------------------------------------------------------------------

def test_onboarding_register_upload_query(client, tmp_storage, mock_ingest, mock_llm, monkeypatch):
    """Full onboarding flow: register tenant, upload doc, query, get answer."""
    import pickle, uuid
    import faiss, numpy as np

    # Register
    reg = client.post(
        "/tenants/register",
        json={"tenant_name": "e2e-team", "team_email": "e2e@example.com"},
        headers=ADMIN,
    )
    assert reg.status_code == 201
    api_key = reg.json()["api_key"]
    h = {"X-Tenant-ID": "e2e-team", "X-API-Key": api_key}

    # Upload doc (ingest stubbed → status=active)
    upload = client.post(
        "/e2e-team/docs/upload",
        files={"file": ("guide.pdf", io.BytesIO(b"%PDF test"), "application/pdf")},
        headers=h,
    )
    assert upload.status_code == 202
    doc_id = upload.json()["doc_id"]

    # Manually seed a tiny FAISS index so the retriever can return something
    dim = 8
    rng = np.random.default_rng(7)
    emb = rng.random((1, dim)).astype(np.float32)
    meta = [{
        "doc_id": doc_id, "tenant_id": "e2e-team", "filename": "guide.pdf",
        "page": 1, "chunk_index": 0,
        "text": "Configuration guide content.",
        "embedding": emb[0].tolist(),
    }]
    faiss_dir = tmp_storage / "tenants" / "e2e-team" / "faiss_index"
    faiss_dir.mkdir(parents=True, exist_ok=True)
    idx = faiss.IndexFlatL2(dim)
    idx.add(emb)
    faiss.write_index(idx, str(faiss_dir / "index.faiss"))
    with open(faiss_dir / "metadata.pkl", "wb") as fh:
        pickle.dump(meta, fh)
    monkeypatch.setattr("vectorstore.retriever.embed_query", lambda q: emb[0].tolist())

    # Query
    query_resp = client.post(
        "/e2e-team/query",
        json={"query": "How do I configure the system?"},
        headers=h,
    )
    assert query_resp.status_code == 200
    body = query_resp.json()
    assert body["fallback"] is False
    # Citation must point back to the uploaded doc
    assert any(c.get("doc_id") == doc_id for c in body.get("citations", []))
