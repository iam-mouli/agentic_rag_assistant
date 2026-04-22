"""Unit tests for tenant API key generation and verification."""

from tenants.auth import generate_api_key, hash_api_key, verify_api_key
from tenants.key_rotation import rotate_key
from tenants.registry import get_tenant_by_id


def test_generate_api_key_returns_hex_string():
    key = generate_api_key()
    assert isinstance(key, str)
    assert len(key) == 64  # secrets.token_hex(32) → 64 hex chars
    assert all(c in "0123456789abcdef" for c in key)


def test_hash_and_verify_api_key():
    key = generate_api_key()
    stored_hash = hash_api_key(key)
    assert verify_api_key(key, stored_hash) is True


def test_invalid_key_fails_verification():
    key = generate_api_key()
    stored_hash = hash_api_key(key)
    assert verify_api_key("wrong-key-value", stored_hash) is False


def test_key_rotation_invalidates_old_key(real_db, tmp_storage, registered_tenant):
    old_key = registered_tenant["api_key"]
    tenant_id = registered_tenant["tenant_id"]

    rotation_result = rotate_key(tenant_id)
    assert rotation_result is not None

    tenant = get_tenant_by_id(tenant_id)
    # Old key must no longer verify against the new hash
    assert verify_api_key(old_key, tenant["api_key_hash"]) is False


def test_new_key_valid_after_rotation(real_db, tmp_storage, registered_tenant):
    tenant_id = registered_tenant["tenant_id"]

    rotation_result = rotate_key(tenant_id)
    new_key = rotation_result["api_key"]
    new_version = rotation_result["api_key_version"]

    tenant = get_tenant_by_id(tenant_id)
    assert verify_api_key(new_key, tenant["api_key_hash"]) is True
    assert tenant["api_key_version"] == new_version
