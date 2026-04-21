from prometheus_client import Counter, Gauge, Histogram

query_total = Counter(
    "rag_query_total",
    "Total queries processed",
    ["tenant_id", "route_decision", "cache_hit"],
)

query_latency_seconds = Histogram(
    "rag_query_latency_seconds",
    "Query latency in seconds",
    ["tenant_id", "node"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0),
)

hallucination_score_histogram = Histogram(
    "rag_hallucination_score",
    "Distribution of hallucination scores",
    ["tenant_id"],
    buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.9, 1.0),
)

guardrail_blocks_total = Counter(
    "rag_guardrail_blocks_total",
    "Total guardrail blocks",
    ["tenant_id", "block_code", "phase"],
)

ingestion_total = Counter(
    "rag_ingestion_total",
    "Total document ingestion attempts",
    ["tenant_id", "status"],
)

active_tenants_gauge = Gauge(
    "rag_active_tenants",
    "Number of active tenants",
)

doc_count_gauge = Gauge(
    "rag_doc_count",
    "Number of indexed documents per tenant",
    ["tenant_id"],
)
