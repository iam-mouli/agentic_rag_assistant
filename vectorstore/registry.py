import sqlite3
from pathlib import Path

from config.settings import settings


def _connect(tenant_id: str) -> sqlite3.Connection:
    db_path = Path(settings.STORAGE_BASE_PATH) / "tenants" / tenant_id / "registry.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_registry(tenant_id: str) -> None:
    conn = _connect(tenant_id)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id        TEXT PRIMARY KEY,
                tenant_id     TEXT NOT NULL,
                filename      TEXT NOT NULL,
                upload_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status        TEXT DEFAULT 'processing',
                version       TEXT,
                chunk_count   INTEGER,
                pages         INTEGER,
                file_hash     TEXT NOT NULL,
                storage_path  TEXT NOT NULL,
                error_message TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def insert_doc(
    tenant_id: str,
    doc_id: str,
    filename: str,
    file_hash: str,
    storage_path: str,
    version: str | None = None,
) -> None:
    conn = _connect(tenant_id)
    try:
        conn.execute(
            """INSERT INTO documents
               (doc_id, tenant_id, filename, file_hash, storage_path, version)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (doc_id, tenant_id, filename, file_hash, storage_path, version),
        )
        conn.commit()
    finally:
        conn.close()


def get_doc(tenant_id: str, doc_id: str) -> dict | None:
    conn = _connect(tenant_id)
    try:
        row = conn.execute(
            "SELECT * FROM documents WHERE doc_id = ? AND tenant_id = ?",
            (doc_id, tenant_id),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_doc_by_hash(tenant_id: str, file_hash: str) -> dict | None:
    conn = _connect(tenant_id)
    try:
        row = conn.execute(
            "SELECT * FROM documents WHERE tenant_id = ? AND file_hash = ? AND status NOT IN ('removed', 'superseded')",
            (tenant_id, file_hash),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_docs(tenant_id: str) -> list[dict]:
    conn = _connect(tenant_id)
    try:
        rows = conn.execute(
            "SELECT * FROM documents WHERE tenant_id = ? AND status NOT IN ('removed', 'superseded') ORDER BY upload_date DESC",
            (tenant_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_doc(tenant_id: str, doc_id: str, **fields) -> None:
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [doc_id, tenant_id]
    conn = _connect(tenant_id)
    try:
        conn.execute(
            f"UPDATE documents SET {set_clause} WHERE doc_id = ? AND tenant_id = ?",
            values,
        )
        conn.commit()
    finally:
        conn.close()
