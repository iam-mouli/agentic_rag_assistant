import uuid
from pathlib import Path

from config.settings import settings
from tenants.auth import generate_api_key, hash_api_key
from tenants.registry import init_db, insert_tenant


def _provision_storage(tenant_name: str) -> str:
    base = Path(settings.STORAGE_BASE_PATH) / "tenants" / tenant_name
    (base / "docs").mkdir(parents=True, exist_ok=True)
    (base / "faiss_index").mkdir(parents=True, exist_ok=True)
    return str(base)


def register_tenant(name: str, team_email: str) -> dict:
    init_db()
    tenant_id = str(uuid.uuid4())
    api_key = generate_api_key()
    storage_path = _provision_storage(name)
    insert_tenant(tenant_id, name, team_email, hash_api_key(api_key), storage_path)
    return {"tenant_id": tenant_id, "api_key": api_key}
