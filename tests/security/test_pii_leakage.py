"""
Security tests — PII leakage prevention.
Verifies that queries containing PII are blocked before reaching the graph.
The current implementation blocks PII queries (returns 422) rather than stripping.
"""

import pytest
from fastapi.testclient import TestClient

from guardrails.input.pii_filter import check_pii


@pytest.fixture
def client(tmp_storage):
    from app.main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def _headers(tenant_info):
    return {"X-Tenant-ID": tenant_info["name"], "X-API-Key": tenant_info["api_key"]}


# ---------------------------------------------------------------------------
# test_query_containing_ssn_is_stripped_before_graph
# ---------------------------------------------------------------------------

def test_query_containing_ssn_is_stripped_before_graph(client, registered_tenant):
    """
    A query with an SSN is intercepted by the input guardrail before the graph.
    The response is 422 (PII_DETECTED) — PII never reaches the LLM.
    """
    resp = client.post(
        f"/{registered_tenant['name']}/query",
        json={"query": "My SSN is 123-45-6789, how do I update my account?"},
        headers=_headers(registered_tenant),
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "PII_DETECTED"


# ---------------------------------------------------------------------------
# test_query_containing_email_is_stripped
# ---------------------------------------------------------------------------

def test_query_containing_email_is_stripped(client, registered_tenant):
    """A query containing an email address is blocked by the PII guardrail."""
    resp = client.post(
        f"/{registered_tenant['name']}/query",
        json={"query": "Please send results to admin@company.com"},
        headers=_headers(registered_tenant),
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "PII_DETECTED"


# ---------------------------------------------------------------------------
# test_pii_strip_does_not_block_request
# ---------------------------------------------------------------------------

def test_pii_strip_does_not_block_request(registered_tenant, seeded_tenant, mock_llm, tmp_storage):
    """
    A clean query (no PII) passes through the input pipeline and returns 200.
    Verifies that non-PII queries are not incorrectly blocked by the PII filter.
    """
    from app.main import app
    with TestClient(app, raise_server_exceptions=True) as client:
        resp = client.post(
            f"/{seeded_tenant['name']}/query",
            json={"query": "How do I configure BIOS settings?"},
            headers=_headers(seeded_tenant),
        )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Unit-level: PII filter detection
# ---------------------------------------------------------------------------

def test_pii_filter_blocks_ssn_unit():
    result = check_pii("SSN 123-45-6789")
    assert not result.passed
    assert "SSN" in result.reason


def test_pii_filter_blocks_email_unit():
    result = check_pii("Email: user@domain.org")
    assert not result.passed
    assert "EMAIL" in result.reason


def test_pii_filter_passes_clean_query_unit():
    result = check_pii("How do I reset the iDRAC password?")
    assert result.passed
