"""Rotating JSONL file handler for structlog.

Writes to storage/logs/app.jsonl; rotates to app.jsonl.1 when the file
exceeds MAX_LOG_BYTES. Both files are read together when querying logs.
"""
import json
from pathlib import Path

from config.settings import settings

_LOG_DIR = Path(settings.STORAGE_BASE_PATH) / "logs"
_LOG_FILE = _LOG_DIR / "app.jsonl"
_ROTATED_FILE = _LOG_DIR / "app.jsonl.1"
MAX_LOG_BYTES = 5 * 1024 * 1024  # 5 MB


def _ensure_dir() -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)


def file_log_processor(logger, method, event_dict: dict) -> dict:
    """structlog processor — appends event to the JSONL file, never raises."""
    try:
        _ensure_dir()
        if _LOG_FILE.exists() and _LOG_FILE.stat().st_size > MAX_LOG_BYTES:
            _LOG_FILE.rename(_ROTATED_FILE)
        with _LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event_dict) + "\n")
    except Exception:
        pass
    return event_dict


def read_logs(
    tenant_id: str | None = None,
    level: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Return log entries newest-first, optionally filtered by tenant and level."""
    lines: list[str] = []

    for path in (_ROTATED_FILE, _LOG_FILE):
        if path.exists():
            try:
                lines.extend(path.read_text(encoding="utf-8").splitlines())
            except Exception:
                pass

    entries: list[dict] = []
    for raw in reversed(lines):
        raw = raw.strip()
        if not raw:
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if tenant_id and entry.get("tenant_id") != tenant_id:
            continue
        if level and entry.get("level", "").lower() != level.lower():
            continue

        entries.append(entry)

    return entries[offset : offset + limit]
