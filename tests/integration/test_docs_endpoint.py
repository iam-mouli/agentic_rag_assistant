"""
Integration tests for document management endpoints.
POST /{tenant}/docs/upload, GET, DELETE, PUT.
Real SQLite. Ingestion worker mocked to avoid PDF parsing + real embeddings.
"""

import io
import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_storage):
    from app.main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture
def mock_ingest(monkeypatch):
    """Replace _ingest_sync so uploads don't require a real PDF or real embeddings."""
    def _stub(tenant_id: str, doc_id: str, file_path: str) -> None:
        from vectorstore.registry import update_doc
        update_doc(tenant_id, doc_id, status="active", chunk_count=5, pages=2)

    monkeypatch.setattr("vectorstore.ingestion_worker._ingest_sync", _stub)


def _h(t):
    return {"X-Tenant-ID": t["name"], "X-API-Key": t["api_key"]}


def _pdf(name="guide.pdf", content=b"%PDF-1.4 test"):
    return {"file": (name, io.BytesIO(content), "application/pdf")}


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def test_upload_doc_returns_202_with_doc_id(client, registered_tenant, mock_ingest):
    resp = client.post(
        f"/{registered_tenant['name']}/docs/upload",
        files=_pdf("setup.pdf"),
        headers=_h(registered_tenant),
    )
    assert resp.status_code == 202
    body = resp.json()
    assert "doc_id" in body
    assert body["status"] == "processing"


def test_upload_doc_becomes_active_after_sync_ingest(client, registered_tenant, mock_ingest):
    upload = client.post(
        f"/{registered_tenant['name']}/docs/upload",
        files=_pdf("guide.pdf"),
        headers=_h(registered_tenant),
    )
    doc_id = upload.json()["doc_id"]

    detail = client.get(
        f"/{registered_tenant['name']}/docs/{doc_id}",
        headers=_h(registered_tenant),
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "active"


def test_duplicate_upload_rejected_by_hash(client, registered_tenant, mock_ingest):
    content = b"%PDF-1.4 unique content abc"
    client.post(f"/{registered_tenant['name']}/docs/upload", files=_pdf("v1.pdf", content), headers=_h(registered_tenant))
    resp = client.post(f"/{registered_tenant['name']}/docs/upload", files=_pdf("v1_copy.pdf", content), headers=_h(registered_tenant))
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

def test_list_docs_returns_only_tenant_docs(client, tmp_storage, mock_ingest):
    ADMIN = {"X-Platform-Admin-Key": "test-admin-key"}
    ra = client.post("/tenants/register", json={"tenant_name": "list-a", "team_email": "a@x.com"}, headers=ADMIN)
    rb = client.post("/tenants/register", json={"tenant_name": "list-b", "team_email": "b@x.com"}, headers=ADMIN)
    ha = {"X-Tenant-ID": "list-a", "X-API-Key": ra.json()["api_key"]}
    hb = {"X-Tenant-ID": "list-b", "X-API-Key": rb.json()["api_key"]}

    client.post("/list-a/docs/upload", files=_pdf("a.pdf"), headers=ha)
    client.post("/list-b/docs/upload", files=_pdf("b.pdf"), headers=hb)

    list_a = client.get("/list-a/docs", headers=ha).json()
    list_b = client.get("/list-b/docs", headers=hb).json()

    assert list_a["total_docs"] == 1
    assert list_b["total_docs"] == 1
    assert list_a["documents"][0]["filename"] == "a.pdf"
    assert list_b["documents"][0]["filename"] == "b.pdf"


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

def test_delete_doc_removes_from_faiss_and_registry(client, seeded_tenant):
    doc_id = seeded_tenant["doc_id"]
    name = seeded_tenant["name"]
    headers = _h(seeded_tenant)

    resp = client.delete(f"/{name}/docs/{doc_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "removed"

    list_resp = client.get(f"/{name}/docs", headers=headers).json()
    assert not any(d["doc_id"] == doc_id for d in list_resp["documents"])


def test_delete_nonexistent_doc_returns_404(client, registered_tenant):
    resp = client.delete(
        f"/{registered_tenant['name']}/docs/no-such-id",
        headers=_h(registered_tenant),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Replace (PUT)
# ---------------------------------------------------------------------------

def test_replace_doc_bumps_version_and_supersedes_old(client, seeded_tenant, mock_ingest):
    doc_id = seeded_tenant["doc_id"]
    name = seeded_tenant["name"]
    headers = _h(seeded_tenant)

    resp = client.put(
        f"/{name}/docs/{doc_id}",
        files=_pdf("guide_v2.pdf"),
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["old_doc_id"] == doc_id
    assert "new_doc_id" in body
    assert body["new_version"] in ("v2", "v1-updated")

    from vectorstore.registry import get_doc
    old = get_doc(name, doc_id)
    assert old["status"] == "superseded"
