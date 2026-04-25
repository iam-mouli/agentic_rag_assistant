import pickle
from pathlib import Path

import faiss
import numpy as np
from langchain_core.documents import Document

from config.settings import settings


def _index_dir(tenant_id: str) -> Path:
    return Path(settings.STORAGE_BASE_PATH) / "tenants" / tenant_id / "faiss_index"


def _load(tenant_id: str) -> tuple[faiss.Index | None, list[dict]]:
    idx_dir = _index_dir(tenant_id)
    index_file = idx_dir / "index.faiss"
    meta_file = idx_dir / "metadata.pkl"

    if not index_file.exists():
        return None, []

    index = faiss.read_index(str(index_file))
    with open(meta_file, "rb") as f:
        metadata = pickle.load(f)
    return index, metadata


def _save(tenant_id: str, index: faiss.Index, metadata: list[dict]) -> None:
    idx_dir = _index_dir(tenant_id)
    idx_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(idx_dir / "index.faiss"))
    with open(idx_dir / "metadata.pkl", "wb") as f:
        pickle.dump(metadata, f)


def add_chunks(tenant_id: str, chunks: list[Document], embeddings: list[list[float]]) -> None:
    if not embeddings:
        return

    index, metadata = _load(tenant_id)

    vectors = np.array(embeddings, dtype=np.float32)
    dim = vectors.shape[1]

    if index is None:
        index = faiss.IndexFlatL2(dim)

    index.add(vectors)

    for chunk, emb in zip(chunks, embeddings):
        metadata.append({
            "doc_id": chunk.metadata.get("doc_id"),
            "tenant_id": chunk.metadata.get("tenant_id"),
            "filename": chunk.metadata.get("filename"),
            "page": chunk.metadata.get("page"),
            "chunk_index": chunk.metadata.get("chunk_index"),
            "text": chunk.page_content,
            "embedding": emb,  # retained for index rebuild on chunk deletion (Phase 4)
        })

    _save(tenant_id, index, metadata)


def search(tenant_id: str, query_embedding: list[float], k: int = 5) -> list[dict]:
    index, metadata = _load(tenant_id)
    if index is None or index.ntotal == 0:
        return []

    query = np.array([query_embedding], dtype=np.float32)
    k = min(k, index.ntotal)
    distances, indices = index.search(query, k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0:
            continue
        entry = {key: val for key, val in metadata[idx].items() if key != "embedding"}
        entry["score"] = float(dist)
        results.append(entry)

    return results


def remove_doc_chunks(tenant_id: str, doc_id: str) -> int:
    """Rebuild FAISS index excluding all chunks belonging to doc_id."""
    index, metadata = _load(tenant_id)
    if index is None:
        return 0

    kept = [m for m in metadata if m["doc_id"] != doc_id]
    removed = len(metadata) - len(kept)
    if removed == 0:
        return 0

    if kept:
        vectors = np.array([m["embedding"] for m in kept], dtype=np.float32)
        dim = vectors.shape[1]
        new_index = faiss.IndexFlatL2(dim)
        new_index.add(vectors)
    else:
        dim = index.d
        new_index = faiss.IndexFlatL2(dim)

    _save(tenant_id, new_index, kept)
    return removed
