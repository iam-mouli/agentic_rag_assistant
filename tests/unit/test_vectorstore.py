"""Unit tests for vectorstore layer. FAISS + registry tested with temp dirs."""

import pickle
import uuid
from pathlib import Path
from unittest.mock import patch

import faiss
import numpy as np
import pytest

from vectorstore.loader import compute_file_hash, load_and_chunk
from vectorstore.registry import (
    get_doc,
    get_doc_by_hash,
    init_registry,
    insert_doc,
    list_docs,
    update_doc,
)
from vectorstore.store import add_chunks, remove_doc_chunks, search


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_doc(content="test content", doc_id="doc1", tenant_id="t1", page=1):
    from langchain_core.documents import Document
    return Document(
        page_content=content,
        metadata={"doc_id": doc_id, "tenant_id": tenant_id, "filename": "test.pdf", "page": page, "chunk_index": 0},
    )


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def test_loader_chunks_pdf_with_metadata(tmp_path):
    from langchain_core.documents import Document

    test_docs = [
        Document(page_content="A" * 1200, metadata={"source": "test.pdf", "page": 0}),
    ]
    with patch("vectorstore.loader.PyPDFLoader") as mock_loader:
        mock_loader.return_value.load.return_value = test_docs
        chunks = load_and_chunk(str(tmp_path / "test.pdf"), "doc-1", "tenant-1")

    assert len(chunks) > 0


def test_loader_attaches_doc_id_and_tenant_id_to_chunks(tmp_path):
    from langchain_core.documents import Document

    test_docs = [Document(page_content="Configuration guide content.", metadata={"source": "test.pdf", "page": 0})]
    with patch("vectorstore.loader.PyPDFLoader") as mock_loader:
        mock_loader.return_value.load.return_value = test_docs
        chunks = load_and_chunk(str(tmp_path / "test.pdf"), "doc-42", "tenant-xyz")

    for chunk in chunks:
        assert chunk.metadata["doc_id"] == "doc-42"
        assert chunk.metadata["tenant_id"] == "tenant-xyz"
        assert "chunk_index" in chunk.metadata


# ---------------------------------------------------------------------------
# Store — insert and retrieve
# ---------------------------------------------------------------------------

def test_store_insert_and_retrieve(tmp_path, monkeypatch):
    from config.settings import settings
    monkeypatch.setattr(settings, "STORAGE_BASE_PATH", str(tmp_path))

    doc = _make_doc("The BIOS configuration procedure is described here.")
    emb = np.random.default_rng(0).random(8).astype(np.float32).tolist()

    add_chunks("t1", [doc], [emb])
    results = search("t1", emb, k=1)

    assert len(results) == 1
    assert results[0]["doc_id"] == "doc1"
    assert "BIOS" in results[0]["text"]


def test_store_delete_removes_chunks_by_doc_id(tmp_path, monkeypatch):
    from config.settings import settings
    monkeypatch.setattr(settings, "STORAGE_BASE_PATH", str(tmp_path))

    rng = np.random.default_rng(1)
    docs = [_make_doc(f"content {i}", doc_id="doc-keep" if i < 2 else "doc-remove") for i in range(4)]
    embs = rng.random((4, 8)).astype(np.float32).tolist()

    add_chunks("t1", docs, embs)

    removed = remove_doc_chunks("t1", "doc-remove")
    assert removed == 2

    remaining = search("t1", embs[0], k=10)
    assert all(r["doc_id"] == "doc-keep" for r in remaining)


# ---------------------------------------------------------------------------
# Registry — insert, get, status transitions
# ---------------------------------------------------------------------------

def test_registry_insert_and_get_doc(tmp_path, monkeypatch):
    from config.settings import settings
    monkeypatch.setattr(settings, "STORAGE_BASE_PATH", str(tmp_path))

    init_registry("tenant-a")
    doc_id = str(uuid.uuid4())
    insert_doc("tenant-a", doc_id, "guide.pdf", "abc123", "/storage/guide.pdf")

    doc = get_doc("tenant-a", doc_id)
    assert doc is not None
    assert doc["filename"] == "guide.pdf"
    assert doc["status"] == "processing"


def test_registry_status_transitions(tmp_path, monkeypatch):
    from config.settings import settings
    monkeypatch.setattr(settings, "STORAGE_BASE_PATH", str(tmp_path))

    init_registry("tenant-b")
    doc_id = str(uuid.uuid4())
    insert_doc("tenant-b", doc_id, "doc.pdf", "hash1", "/path/doc.pdf")

    # processing → active
    update_doc("tenant-b", doc_id, status="active", chunk_count=10, pages=3)
    doc = get_doc("tenant-b", doc_id)
    assert doc["status"] == "active"
    assert doc["chunk_count"] == 10

    # active → removed
    update_doc("tenant-b", doc_id, status="removed")
    doc = get_doc("tenant-b", doc_id)
    assert doc["status"] == "removed"

    # Removed docs excluded from list
    visible = list_docs("tenant-b")
    assert not any(d["doc_id"] == doc_id for d in visible)


def test_hash_dedup_blocks_duplicate_upload(tmp_path, monkeypatch):
    from config.settings import settings
    monkeypatch.setattr(settings, "STORAGE_BASE_PATH", str(tmp_path))

    init_registry("tenant-c")
    file_hash = "deadbeef" * 8
    insert_doc("tenant-c", "doc-1", "report.pdf", file_hash, "/path/report.pdf")
    update_doc("tenant-c", "doc-1", status="active")

    duplicate = get_doc_by_hash("tenant-c", file_hash)
    assert duplicate is not None
    assert duplicate["doc_id"] == "doc-1"
