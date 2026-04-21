from tenants.auth import generate_api_key, hash_api_key
from tenants.registry import get_tenant_by_id, update_tenant


def rotate_key(tenant_id: str) -> dict | None:
    tenant = get_tenant_by_id(tenant_id)
    if not tenant:
        return None

    new_key = generate_api_key()
    new_version = tenant["api_key_version"] + 1
    update_tenant(tenant_id, api_key_hash=hash_api_key(new_key), api_key_version=new_version)

    # Phase 7: invalidate Redis cache entry keyed by (hash, tenant_id)

    return {
        "tenant_id": tenant_id,
        "api_key": new_key,           # returned once — not stored in plaintext
        "api_key_version": new_version,
    }
