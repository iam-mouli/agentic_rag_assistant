import sqlite3
from pathlib import Path

from config.settings import settings


def _connect() -> sqlite3.Connection:
    db_path = Path(settings.MASTER_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                tenant_id             TEXT PRIMARY KEY,
                name                  TEXT UNIQUE NOT NULL,
                team_email            TEXT NOT NULL,
                api_key_hash          TEXT NOT NULL,
                api_key_version       INTEGER DEFAULT 1,
                status                TEXT DEFAULT 'active',
                created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                doc_count             INTEGER DEFAULT 0,
                storage_path          TEXT NOT NULL,
                qps_limit             INTEGER DEFAULT 10,
                monthly_token_budget  INTEGER DEFAULT 5000000,
                tokens_used_month     INTEGER DEFAULT 0
            )
        """)
        conn.commit()
    finally:
        conn.close()


def insert_tenant(
    tenant_id: str,
    name: str,
    team_email: str,
    api_key_hash: str,
    storage_path: str,
) -> None:
    conn = _connect()
    try:
        conn.execute(
            """INSERT INTO tenants
               (tenant_id, name, team_email, api_key_hash, storage_path)
               VALUES (?, ?, ?, ?, ?)""",
            (tenant_id, name, team_email, api_key_hash, storage_path),
        )
        conn.commit()
    finally:
        conn.close()


def get_tenant_by_name(name: str) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM tenants WHERE name = ?", (name,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_tenant_by_id(tenant_id: str) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM tenants WHERE tenant_id = ?", (tenant_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_tenants() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM tenants ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_tenant(tenant_id: str, **fields) -> None:
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [tenant_id]
    conn = _connect()
    try:
        conn.execute(
            f"UPDATE tenants SET {set_clause} WHERE tenant_id = ?", values
        )
        conn.commit()
    finally:
        conn.close()


def deactivate_tenant(tenant_id: str) -> None:
    update_tenant(tenant_id, status="deactivated")
