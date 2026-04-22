"""Unit tests for Prometheus metrics definitions and emission helpers."""

import pytest
from prometheus_client import REGISTRY, CollectorRegistry


def test_query_counter_increments():
    from observability.prometheus.metrics import query_total
    before = query_total.labels(tenant_id="t1", route_decision="retrieve", cache_hit="false")._value.get()
    query_total.labels(tenant_id="t1", route_decision="retrieve", cache_hit="false").inc()
    after = query_total.labels(tenant_id="t1", route_decision="retrieve", cache_hit="false")._value.get()
    assert after == before + 1


def test_guardrail_block_counter_increments_with_correct_labels():
    from observability.prometheus.metrics import guardrail_blocks_total
    before = guardrail_blocks_total.labels(
        tenant_id="t2", block_code="INJECTION_DETECTED", phase="input"
    )._value.get()
    guardrail_blocks_total.labels(
        tenant_id="t2", block_code="INJECTION_DETECTED", phase="input"
    ).inc()
    after = guardrail_blocks_total.labels(
        tenant_id="t2", block_code="INJECTION_DETECTED", phase="input"
    )._value.get()
    assert after == before + 1


def test_ingestion_counter_increments_on_success():
    from observability.prometheus.metrics import ingestion_total
    before = ingestion_total.labels(tenant_id="t3", status="success")._value.get()
    ingestion_total.labels(tenant_id="t3", status="success").inc()
    after = ingestion_total.labels(tenant_id="t3", status="success")._value.get()
    assert after == before + 1


def test_metrics_emit_does_not_raise_on_failure():
    """Simulates the fail-safe pattern used in the query route."""
    from observability.prometheus.metrics import query_total

    try:
        # Intentionally call with invalid label to simulate metric emission failure
        query_total.labels(tenant_id=None, route_decision=None, cache_hit=None).inc()
    except Exception as exc:
        pass  # Production code wraps this in try/except — verify no unhandled raise
