"""
Security tests — rate-limit enforcement.
QPS and monthly token budget limits tested by mocking Redis helpers.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_storage):
    from app.main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def _headers(t):
    return {"X-Tenant-ID": t["name"], "X-API-Key": t["api_key"]}


# ---------------------------------------------------------------------------
# test_requests_above_qps_limit_return_429
# ---------------------------------------------------------------------------

def test_requests_above_qps_limit_return_429(client, seeded_tenant, mock_llm, monkeypatch):
    async def _always_rate_limited(redis, tenant_id, qps_limit):
        return False, 1

    monkeypatch.setattr("app.middleware.rate_limiter._check_qps", _always_rate_limited)

    from app.main import app
    app.state.redis = object()
    try:
        resp = client.post(
            f"/{seeded_tenant['name']}/query",
            json={"query": "How do I configure alerts?"},
            headers=_headers(seeded_tenant),
        )
        assert resp.status_code == 429
        assert resp.headers["X-Quota-Exceeded"] == "qps"
        assert "Retry-After" in resp.headers
    finally:
        app.state.redis = None


# ---------------------------------------------------------------------------
# test_requests_within_qps_limit_succeed
# ---------------------------------------------------------------------------

def test_requests_within_qps_limit_succeed(client, seeded_tenant, mock_llm, monkeypatch):
    async def _always_allowed(redis, tenant_id, qps_limit):
        return True, 0

    monkeypatch.setattr("app.middleware.rate_limiter._check_qps", _always_allowed)

    from app.main import app
    app.state.redis = object()
    try:
        resp = client.post(
            f"/{seeded_tenant['name']}/query",
            json={"query": "How do I configure the system?"},
            headers=_headers(seeded_tenant),
        )
        assert resp.status_code == 200
    finally:
        app.state.redis = None


# ---------------------------------------------------------------------------
# test_monthly_token_budget_exceeded_returns_429
# ---------------------------------------------------------------------------

def test_monthly_token_budget_exceeded_returns_429(client, seeded_tenant, mock_llm, monkeypatch):
    from tenants.registry import update_tenant
    update_tenant(seeded_tenant["tenant_id"], tokens_used_month=5_000_001, monthly_token_budget=5_000_000)

    async def _qps_allowed(redis, tenant_id, qps_limit):
        return True, 0

    monkeypatch.setattr("app.middleware.rate_limiter._check_qps", _qps_allowed)

    from app.main import app
    app.state.redis = object()
    try:
        resp = client.post(
            f"/{seeded_tenant['name']}/query",
            json={"query": "How do I configure alerts?"},
            headers=_headers(seeded_tenant),
        )
        assert resp.status_code == 429
        assert resp.headers["X-Quota-Exceeded"] == "monthly_tokens"
    finally:
        app.state.redis = None


# ---------------------------------------------------------------------------
# test_rate_limiter_fails_open_when_redis_down
# ---------------------------------------------------------------------------

def test_rate_limiter_fails_open_when_redis_down(client, seeded_tenant, mock_llm):
    """Redis is None in the test environment → rate limiter skips and request succeeds."""
    from app.main import app
    assert getattr(app.state, "redis", None) is None

    resp = client.post(
        f"/{seeded_tenant['name']}/query",
        json={"query": "How do I configure the system?"},
        headers=_headers(seeded_tenant),
    )
    assert resp.status_code == 200
