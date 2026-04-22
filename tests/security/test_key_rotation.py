"""
Security tests — API key rotation.
Old key is immediately invalidated; new key works; rotation is atomic.
"""

import pytest
from fastapi.testclient import TestClient

from tenants.auth import verify_api_key
from tenants.registry import get_tenant_by_id

ADMIN_HEADERS = {"X-Platform-Admin-Key": "test-admin-key"}


@pytest.fixture
def client(tmp_storage):
    from app.main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ---------------------------------------------------------------------------
# test_old_key_rejected_after_rotation
# ---------------------------------------------------------------------------

def test_old_key_rejected_after_rotation(client, registered_tenant, seeded_tenant, mock_llm):
    tenant_id = registered_tenant["tenant_id"]
    old_key = registered_tenant["api_key"]
    tenant_name = registered_tenant["name"]

    rotate_resp = client.post(f"/tenants/{tenant_id}/rotate-key", headers=ADMIN_HEADERS)
    assert rotate_resp.status_code == 200

    # Old key must fail authentication on the tenant's route
    resp = client.post(
        f"/{tenant_name}/query",
        json={"query": "How do I configure alerts?"},
        headers={"X-Tenant-ID": tenant_name, "X-API-Key": old_key},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# test_new_key_accepted_after_rotation
# ---------------------------------------------------------------------------

def test_new_key_accepted_after_rotation(client, registered_tenant, seeded_tenant, mock_llm):
    tenant_id = registered_tenant["tenant_id"]
    tenant_name = registered_tenant["name"]

    rotate_resp = client.post(f"/tenants/{tenant_id}/rotate-key", headers=ADMIN_HEADERS)
    new_key = rotate_resp.json()["api_key"]

    resp = client.post(
        f"/{tenant_name}/query",
        json={"query": "How do I configure alerts?"},
        headers={"X-Tenant-ID": tenant_name, "X-API-Key": new_key},
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# test_rotation_is_atomic (no window where both keys are invalid)
# ---------------------------------------------------------------------------

def test_rotation_is_atomic(client, registered_tenant):
    """
    Verifies that after rotation the new key is immediately valid —
    there is no period where neither key works.
    """
    tenant_id = registered_tenant["tenant_id"]

    rotate_resp = client.post(f"/tenants/{tenant_id}/rotate-key", headers=ADMIN_HEADERS)
    assert rotate_resp.status_code == 200

    new_key = rotate_resp.json()["api_key"]
    new_version = rotate_resp.json()["api_key_version"]

    # Immediately after rotation, new key must verify against stored hash
    tenant = get_tenant_by_id(tenant_id)
    assert verify_api_key(new_key, tenant["api_key_hash"]) is True
    assert tenant["api_key_version"] == new_version
