import json
import sqlite3
import uuid
from pathlib import Path

from config.settings import settings


def _connect(tenant_id: str) -> sqlite3.Connection:
    db_path = Path(settings.STORAGE_BASE_PATH) / "tenants" / tenant_id / "history.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_history(tenant_id: str) -> None:
    conn = _connect(tenant_id)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_history (
                query_id         TEXT PRIMARY KEY,
                tenant_id        TEXT NOT NULL,
                query            TEXT NOT NULL,
                answer           TEXT NOT NULL,
                citations        TEXT,
                confidence       REAL,
                confidence_level TEXT,
                fallback         INTEGER DEFAULT 0,
                run_id           TEXT,
                cache_hit        INTEGER DEFAULT 0,
                created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_tenant_created "
            "ON query_history (tenant_id, created_at DESC)"
        )
        conn.commit()
    finally:
        conn.close()


def save_query(
    tenant_id: str,
    query: str,
    answer: str,
    citations: list,
    confidence: float,
    confidence_level: str,
    fallback: bool,
    run_id: str | None,
    cache_hit: bool,
) -> str:
    query_id = str(uuid.uuid4())
    conn = _connect(tenant_id)
    try:
        conn.execute(
            """INSERT INTO query_history
               (query_id, tenant_id, query, answer, citations,
                confidence, confidence_level, fallback, run_id, cache_hit)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                query_id,
                tenant_id,
                query,
                answer,
                json.dumps(citations),
                confidence,
                confidence_level,
                int(fallback),
                run_id,
                int(cache_hit),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return query_id


def list_history(tenant_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
    conn = _connect(tenant_id)
    try:
        rows = conn.execute(
            """SELECT * FROM query_history
               WHERE tenant_id = ?
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            (tenant_id, limit, offset),
        ).fetchall()
        entries = []
        for row in rows:
            entry = dict(row)
            try:
                entry["citations"] = json.loads(entry["citations"] or "[]")
            except (json.JSONDecodeError, TypeError):
                entry["citations"] = []
            entry["fallback"] = bool(entry["fallback"])
            entry["cache_hit"] = bool(entry["cache_hit"])
            entries.append(entry)
        return entries
    finally:
        conn.close()


def delete_query(tenant_id: str, query_id: str) -> bool:
    conn = _connect(tenant_id)
    try:
        cur = conn.execute(
            "DELETE FROM query_history WHERE query_id = ? AND tenant_id = ?",
            (query_id, tenant_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def clear_history(tenant_id: str) -> int:
    conn = _connect(tenant_id)
    try:
        cur = conn.execute(
            "DELETE FROM query_history WHERE tenant_id = ?",
            (tenant_id,),
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()
