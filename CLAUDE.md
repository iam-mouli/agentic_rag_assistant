# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A multi-tenant Enterprise Knowledge Base Platform enabling any product team to onboard documentation and get an AI knowledge assistant with zero platform-team dependency. The authoritative spec is `agentic-rag-platform-design.md` (v1.3).

**Target state:** Agentic multi-tenant platform using LangGraph, self-serve tenant onboarding, hallucination grading, and full observability.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Framework | LangGraph |
| LLMs | OpenAI / Anthropic / Gemini — configurable via `LLM_PROVIDER` |
| Embeddings | OpenAI / Gemini — configurable via `EMBEDDING_PROVIDER` |
| Vector Store | FAISS (per-tenant, isolated) |
| API | FastAPI + Pydantic |
| Task Queue | arq (Redis-backed async ingestion) |
| Cache | Redis (semantic cache + rate limits + write locks) |
| DB | SQLite (dev) / PostgreSQL (prod) for tenant + doc registry |
| Guardrails | NeMo Guardrails + custom validators |
| Tracing | LangSmith |
| Metrics | Prometheus + Grafana |
| Logging | structlog (JSON) |
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind CSS + TanStack Query |

## Commands

```bash
# Dev server
uvicorn app.main:app --reload                          # API on port 8000

# Async ingestion worker
arq vectorstore.ingestion_worker.WorkerSettings

# Full stack (Redis, Prometheus, Grafana)
docker-compose up --build

# Tests
pytest tests/unit/
pytest tests/integration/
pytest tests/unit/test_<module>.py::test_<name>        # Single test
python tests/eval/run_evals.py                         # LangSmith evals (CI-gated)
```

## Architecture

### Multi-Tenancy

- **Isolation:** Each tenant gets `storage/tenants/{tenant_name}/docs/`, `faiss_index/`, `registry.db`
- **Shared:** LangGraph engine, guardrails, LLM clients, prompts
- **Auth:** `X-Tenant-ID` + `X-API-Key` headers; keys stored as argon2id hashes in master `tenants.db`
- **Quotas:** Per-tenant QPS limit (default 10) + monthly token budget (default 5M)
- **Write safety:** Redis SETNX lock (TTL 10 min) per tenant before any FAISS write

### LangGraph Agent (`graph/`)

GraphState carries: `query`, `rewritten_query`, `documents`, `generation`, `hallucination_score`, `answer_score`, `route_decision`, `citations`, `fallback`, `tenant_id`, `rewrite_count`.

```
Router → Retriever → DocGrader → Generator → HallucinationGrader → AnswerGrader → END
                         ↓ (all chunks fail grading)
                    QueryRewriter → back to Retriever (max 3 rewrites → Fallback)
```

- Router can short-circuit to direct-answer path (bypasses retrieval + citation enforcement)
- Self-correction loop: poor retrieval → query rewrite → retry (capped at `MAX_REWRITE_ATTEMPTS=3`)

### LLM Client (`llm/client.py`)

Provider-agnostic factory with lazy init. Switch provider via env var — no code changes:
- `LLM_PROVIDER=openai` → gpt-4o (generation) + gpt-4o-mini (grading)
- `LLM_PROVIDER=anthropic` → claude-sonnet-4-6 (generation) + claude-haiku-4-5-20251001 (grading)
- `LLM_PROVIDER=gemini` → gemini-2.0-flash (generation) + gemini-2.0-flash-lite (grading)
- `EMBEDDING_PROVIDER` → `openai` or `gemini` (Anthropic has no embedding model)

### Key Thresholds (`config/constants.py`)

```python
MAX_REWRITE_ATTEMPTS = 3
HALLUCINATION_THRESHOLD = 0.75
ANSWER_SCORE_THRESHOLD = 0.70
TOP_K_RETRIEVAL = 5
CHUNK_SIZE = 1000
SEMANTIC_CACHE_TTL = 3600
```

### Guardrails (`guardrails/`)

Two-phase, decoupled from graph — update independently:
- **Input:** topic_checker, pii_filter, injection_detector, length_validator
- **Output:** hallucination_gate (≥0.75), citation_enforcer, toxicity_filter, confidence_tagger
- **Injection defense:** chunk-time classifier quarantines flagged content; generator prompt hardened with XML wrapping
- All guardrails use `GuardrailResult(passed, block_code, reason)`. Input pipeline short-circuits on first failure (HTTP 422). Output pipeline does the same.
- `confidence_level: str` (`"high"` / `"medium"` / `"low"`) is included in every `QueryResponse`.

### Document Ingestion (`vectorstore/`)

- Async via arq worker → 202 Accepted, client polls for status
- Two-layer storage: SQLite doc registry (`registry.db`) + FAISS vectors (each chunk carries `doc_id` + `tenant_id`)
- Deletion removes from both FAISS index and SQLite registry atomically

### Request Flow

```
Request → Middleware (tenant validate, rate limit) → Semantic cache check
→ Input guardrails → Graph execution → Output guardrails → Cache populate → Response
```

## API Endpoints

```
POST /tenants/register               # Self-serve onboarding
GET  /tenants/{tenant_id}            # Tenant status
POST /tenants/{tenant_id}/rotate-key # API key rotation
POST /{tenant_id}/query              # Query with citations
POST /{tenant_id}/docs/upload        # Upload doc (202 async)
GET  /{tenant_id}/docs               # List docs
GET  /{tenant_id}/docs/{doc_id}      # Get doc metadata
DELETE /{tenant_id}/docs/{doc_id}    # Remove doc
PUT  /{tenant_id}/docs/{doc_id}      # Replace doc (new version)
POST /{tenant_id}/feedback           # Thumbs-up/down wired to LangSmith run_id
GET  /health, /health/{tenant_id}    # Status
GET  /metrics                        # Prometheus scrape
```

## Configuration

Copy `.env.example` to `.env`. Set the API key for your chosen provider plus `PLATFORM_ADMIN_KEY` and Redis connection.

All settings go through `config/settings.py` (Pydantic `BaseSettings`). All numeric thresholds live in `config/constants.py` — change them there, not inline.

---

## Implementation Phases

| # | Status | Deliverable |
|---|--------|-------------|
| 1 | **Completed** | Core agentic RAG graph, LLM client, vectorstore |
| 2 | **Completed** | Query REST API wired to graph |
| 3 | **Completed** | Multi-tenant foundation — auth, registry, middleware, rate limiting |
| 4 | **Completed** | Per-tenant doc management + async arq ingestion |
| 5 | **Completed** | Guardrails — input + output + indirect injection defense |
| 6 | **Completed** | Tracing + structured logs (LangSmith, structlog) |
| 7 | **Completed** | Metrics + dashboards + semantic cache |
| 8 | **Completed** | Full test suite + security tests |
| 9 | **Completed** | Next.js tenant frontend + CORS middleware + feedback endpoint + docker-compose |

Do not skip ahead — each phase depends on the previous. The design doc is the source of truth for implementation details.

---

## Phase Handoff Notes

### Phase 1 — Core Agentic RAG Graph
**Commit:** `86f1fd9`

**What was built:**
- `graph/state.py` — `GraphState` TypedDict (11 fields)
- `graph/nodes/` — 7 nodes: router, retriever, doc_grader, generator, hallucination_grader, answer_grader, query_rewriter + fallback
- `graph/edges/conditions.py` — 6 conditional edge functions
- `graph/builder.py` — compiled `StateGraph`; module-level `rag_graph = build_graph()`
- `llm/client.py` — provider-agnostic lazy-init factory (OpenAI / Anthropic / Gemini)
- `vectorstore/store.py` — FAISS `IndexFlatL2` with pickle metadata sidecar
- `vectorstore/loader.py` — PDF + text chunking with `doc_id`/`tenant_id` metadata
- `vectorstore/embedder.py` — thin wrapper over `llm/client.py` embed()
- `prompts/` — all system prompts as plain strings

**Non-obvious decisions:**
- `generate()` and `grade()` in `llm/client.py` are **synchronous**. LangGraph's `ainvoke()` runs sync nodes via thread pool automatically — do not convert them to async without removing that assumption.
- Generator node sets `answer_score=1.0` on the direct-answer path (router bypasses retrieval). Without this, the API returned confidence=0.0.
- `check_loop_limit` is a conditional edge **after** `query_rewriter`, not after retriever. It routes to `fallback` when `rewrite_count >= MAX_REWRITE_ATTEMPTS`.
- FAISS `IndexFlatL2` has no native delete. Embeddings are stored alongside chunk text in the pickle sidecar. On deletion the entire index is rebuilt from the kept entries.

---

### Phase 2 — Query REST API
**Commit:** `6c891ee` (plus bug fixes in `c919295`)

**What was built:**
- `app/routes/query.py` — `POST /{tenant_id}/query` endpoint
- `app/schemas/query.py` — `QueryRequest` / `QueryResponse` Pydantic models
- `app/main.py` — FastAPI app skeleton, lifespan (graph compile on startup)

**Non-obvious decisions:**
- State is initialized via `_build_initial_state()` (a function), not a module-level dict. A shared mutable dict default caused list fields (`documents`, `citations`) to bleed across requests.
- `rag_graph.ainvoke()` is called from an async route — works because LangGraph wraps sync nodes in a thread pool executor.

---

### Phase 3 — Multi-Tenant Foundation
**Commit:** `ec311ea`

**What was built:**
- `tenants/auth.py` — argon2id key hashing via `argon2-cffi`; `generate_api_key()` returns `secrets.token_hex(32)`
- `tenants/registry.py` — master `tenants.db` SQLite CRUD; schema includes qps_limit, monthly_token_budget, tokens_used_month
- `tenants/key_rotation.py` — atomic key rotation (new hash written before old invalidated)
- `app/routes/tenants.py` — register, get status, rotate key endpoints
- `app/middleware/tenant_resolver.py` — validates `X-Tenant-ID` + `X-API-Key`; cross-tenant path guard
- `app/middleware/rate_limiter.py` — Redis sorted-set QPS sliding window + monthly token budget; fails open if Redis is down

**Non-obvious decisions:**
- Middleware is added in **LIFO order** in FastAPI/Starlette. `add_middleware(RateLimiterMiddleware)` is called **before** `add_middleware(TenantResolverMiddleware)` so that TenantResolver runs first and populates `request.state.tenant` before RateLimiter reads it.
- `/tenants/*` routes require `X-Platform-Admin-Key` (not tenant key). The resolver skips normal tenant validation for these paths.
- Cross-tenant guard: the first path segment is compared against the `X-Tenant-ID` header. A tenant cannot reach another tenant's routes even with a valid key.
- Rate limiter fails **open** (allows the request) when Redis is unavailable. This is intentional to avoid Redis outage = full platform outage.

---

### Phase 4 — Per-Tenant Doc Management + Async Ingestion
**Commit:** `8e957b6`

**What was built:**
- `vectorstore/registry.py` — per-tenant `registry.db`; doc status lifecycle: `processing → active | failed`; superseded/removed on update/delete
- `vectorstore/ingestion_worker.py` — arq job `index_document`; acquires per-tenant Redis SETNX write lock before touching FAISS; `_ingest_sync` is shared with the dev fallback (no arq worker needed in dev)
- `app/routes/docs.py` — 5 endpoints: upload (202, SHA-256 dedup), list, get, delete, replace (PUT bumps version)
- `app/main.py` — arq pool created in lifespan; `app.state.arq_pool` used by upload/update routes

**Non-obvious decisions:**
- Upload saves to a temp file (`_tmp_<uuid>_<name>`), computes hash, checks for duplicate, then atomically renames to final path. Temp file is cleaned up on any error path.
- `_enqueue_or_ingest()` checks `request.app.state.arq_pool` — if absent (no Redis / dev mode), it falls back to calling `_ingest_sync` directly in-process. This means uploads are **synchronous in dev** but async in prod.
- `PUT /{tenant_id}/docs/{doc_id}` (replace) marks the old doc `superseded`, removes its FAISS chunks, then inserts a new doc record with bumped version (`v1 → v2`). The old record is retained in the registry for audit purposes.
- Hash dedup only checks docs with status **not in** `('removed', 'superseded')`. Re-uploading a previously removed document is allowed.
- `arq_pool.aclose()` is called before `redis.aclose()` in lifespan teardown — order matters since arq pool holds its own Redis connection.

---

### Phase 5 — Guardrails
**Commit:** *(see git log)*

**What was built:**
- `guardrails/models.py` — `GuardrailResult(passed, block_code, reason)` dataclass shared by all validators
- `guardrails/input/length_validator.py` — enforces `MIN_QUERY_LENGTH` / `MAX_QUERY_LENGTH` from constants
- `guardrails/input/injection_detector.py` — regex for 11 prompt-injection patterns (ignore instructions, jailbreak, role-hijack, `[system]` tags, DAN)
- `guardrails/input/pii_filter.py` — regex for SSN, credit card, email, US phone, passport
- `guardrails/input/topic_checker.py` — permissive keyword block; only rejects queries clearly outside enterprise/tech (recipes, horoscopes, gambling, etc.)
- `guardrails/input/__init__.py` — `run_input_guardrails(query)` pipeline (cheapest → most expensive; short-circuits on first failure)
- `guardrails/output/hallucination_gate.py` — blocks if `hallucination_score < HALLUCINATION_THRESHOLD`; skips for fallback answers
- `guardrails/output/citation_enforcer.py` — blocks RAG responses with no citations; skips `direct_answer` path and fallback
- `guardrails/output/toxicity_filter.py` — regex for profanity/slurs/hate speech in generated text
- `guardrails/output/confidence_tagger.py` — `tag_confidence(score) → "high"|"medium"|"low"` (≥0.85 / ≥0.70 / below); gate always passes
- `guardrails/output/__init__.py` — `run_output_guardrails(result)` pipeline
- `guardrails/indirect_injection/chunk_classifier.py` — `classify_chunk(text) → bool`; quarantines chunks containing injection patterns or data-exfiltration markdown links
- `app/routes/query.py` — input guardrails before `rag_graph.ainvoke`; output guardrails after; both raise HTTP 422 `{code, reason}` on failure; `confidence_level` added to response
- `app/schemas/response.py` — added `confidence_level: str` field to `QueryResponse`
- `vectorstore/ingestion_worker.py` — filters each chunk through `classify_chunk` before embedding; quarantined chunks are logged (`indirect_injection_quarantine`) and excluded from FAISS; `chunk_count` reflects only safe chunks

**Non-obvious decisions:**
- Input pipeline order: length → injection → PII → topic. Cheapest checks first to minimise unnecessary regex work. Short-circuits on first failure — the first blocked check's `block_code` is returned.
- `topic_checker` is **permissive by design**: it only blocks queries that are unambiguously unrelated to enterprise tech. False-negative (off-topic query passes) is far less harmful than false-positive (legitimate enterprise query blocked).
- `hallucination_gate` skips when `result["fallback"] is True`. Fallback answers are intentionally not document-grounded; applying the hallucination gate to them would always block them.
- `citation_enforcer` checks `route_decision == "direct_answer"` OR `fallback == True` to skip. Both legitimate paths produce citations-free answers.
- `classify_chunk` returning `False` does **not** fail the ingestion job — it logs and skips the chunk. Quarantining a few adversarial chunks should not prevent an entire doc from being indexed.
- `confidence_level` thresholds: high ≥ 0.85, medium ≥ `ANSWER_SCORE_THRESHOLD` (0.70), low otherwise. These differ from `ANSWER_SCORE_THRESHOLD` intentionally — the score threshold gates the *graph's* self-correction loop, while the confidence label is a *client-facing* signal.

---

### Phase 6 — Tracing + Structured Logs
**Commit:** `83b5f44`

**What was built:**
- `observability/logging/structured_logger.py` — `configure_logging()` sets up structlog JSON renderer with `merge_contextvars`, ISO timestamps, exc_info formatting; `get_logger(name)` factory used by all modules
- `observability/langsmith/tracer.py` — `trace_graph_run(tenant_id, query)` async context manager: opens a LangSmith run on entry, annotates it with `tenant_id`, `route_decision`, `rewrite_count`, `hallucination_score`, `answer_score`, `fallback` on exit; `populate_carrier(carrier, result)` copies graph output into the carrier; `get_run_id(carrier)` returns the UUID for the response header
- `observability/graph_tracing.py` — `traced_node(name, fn)` wraps any node callable to emit `graph_node_enter` / `graph_node_exit` / `graph_node_error` with `latency_ms`
- `graph/builder.py` — all `add_node()` calls wrapped with `traced_node()`
- `app/main.py` — `configure_logging()` called at module load; `get_logger()` replaces any bare logging
- `app/routes/query.py` — binds `request_id` + `tenant_id` as structlog context vars per request; logs `guardrail_input_block` and `guardrail_output_block` (with `block_code` + `query_excerpt[:80]`) + `query_completed` with full graph metrics; returns `X-Run-ID` header
- `vectorstore/ingestion_worker.py` — stdlib `logger = logging.getLogger()` replaced with `get_logger()`; emits `doc_ingested` (chunk_count, quarantined_count, pages), `chunk_quarantined` (chunk_index), `ingestion_failed` (error) events

**Non-obvious decisions:**
- LangSmith is **fully opt-in**: `trace_graph_run` is a no-op context manager when `LANGSMITH_API_KEY` is absent or `langsmith` is not installed. Call-sites need no conditional logic — the carrier dict is always yielded.
- Guardrail block logs in `query.py` are emitted **before** raising `HTTPException` — they always fire even if the exception path short-circuits LangSmith. This satisfies the security-relevance requirement.
- `structlog.contextvars.bind_contextvars(request_id=..., tenant_id=...)` is called at the top of each query handler after `clear_contextvars()`. All subsequent log calls within that request (including deep inside nodes) automatically inherit those fields without being passed explicitly.
- `traced_node` is a plain synchronous wrapper. LangGraph's thread-pool executor handles sync node dispatch — the wrapper does not need to be async.
- `X-Run-ID` header is only set when LangSmith is enabled (i.e., `run_id` is non-None). When tracing is disabled the header is simply absent — no sentinel value is emitted.

---

### Phase 7 — Metrics + Dashboards + Semantic Cache
**Commit:** `Phase 7 complete: metrics + dashboards + semantic cache`

**What was built:**
- `observability/prometheus/metrics.py` — 6 Prometheus instruments: `rag_query_total` (Counter, labels: tenant_id, route_decision, cache_hit), `rag_query_latency_seconds` (Histogram, labels: tenant_id, node), `rag_hallucination_score` (Histogram, labels: tenant_id), `rag_guardrail_blocks_total` (Counter, labels: tenant_id, block_code, phase), `rag_ingestion_total` (Counter, labels: tenant_id, status), `rag_active_tenants` / `rag_doc_count` (Gauges)
- `observability/semantic_cache.py` — Redis-backed semantic similarity cache; `get()` embeds the incoming query and cosine-compares against all stored embeddings for the tenant; `set()` stores embedding + serialised response under a tenant-scoped index key; `invalidate_tenant()` bulk-deletes all cache keys for a tenant
- `app/routes/query.py` — cache check placed **before** input guardrails; on hit: emits `cache_hit="true"` metrics, sets `cache: True` in response body, returns early; on miss: runs full graph + guardrails, emits `cache_hit="false"` + hallucination histogram, populates cache after response is built; guardrail blocks emit `guardrail_blocks_total`; all metric calls wrapped in `try/except`
- `app/routes/docs.py` — `invalidate_tenant()` called after upload, delete, and replace (PUT) so stale cache entries never serve outdated answers
- `vectorstore/ingestion_worker.py` — `ingestion_total` incremented for `success`, `quarantined` (if any chunks were quarantined), and `failed`; `doc_count_gauge` incremented on success
- `docker/grafana/dashboard_platform.json` — platform-wide dashboard: Queries/min by Tenant (timeseries), Cache Hit Rate % (gauge), Guardrail Block Rate by block_code (timeseries), Hallucination Score Distribution (histogram), Ingestion Rate by Status (timeseries), P95 Query Latency (timeseries)
- `docker/grafana/dashboard_tenant.json` — per-tenant drilldown with `$tenant_id` template variable (populated from `label_values(rag_query_total, tenant_id)`); same panels scoped to the selected tenant plus Doc Inventory Count (stat) and Node Latency Breakdown P50/P95

**Non-obvious decisions:**
- Cache check is the **first** thing in the query handler (before even input guardrails). A cache hit means the original query already passed all guardrails — re-running them on an identical semantically-equivalent query is waste.
- Semantic cache is **fail-open** throughout: `get()`, `set()`, and `invalidate_tenant()` all catch every exception and log a warning rather than propagating. Redis unavailability must never kill a query.
- `invalidate_tenant()` is called on upload/delete/replace even when the operation succeeds. The tenant's full document set has changed, so all cached answers are potentially stale — selective invalidation would require knowing which cached answers used which documents.
- `cache_hit` label is a string (`"true"` / `"false"`) not a boolean. Prometheus label values are always strings; using Python booleans would produce the label value `True` which is inconsistent with PromQL conventions.
- All metric emissions are wrapped in `try/except` — a Prometheus client error (e.g., label cardinality explosion) must not kill a live request or ingestion job.
- Grafana dashboards use datasource `"Prometheus"` (capital P) — case-sensitive match to the provisioned datasource name. Using lowercase would silently break all panels.
- Both dashboards use `schemaVersion: 38` (Grafana 10 format). The `__inputs` / `__requires` blocks make them importable via the Grafana UI without manual datasource selection.

---

### Phase 8 — Full Test Suite + Security Tests
**Commit:** *(see git log)*

**What was built:**

`tests/conftest.py` — shared fixtures for all layers:
- `tmp_storage` — monkeypatches `settings.STORAGE_BASE_PATH` and `settings.MASTER_DB_PATH` on the singleton object so all modules see `tmp_path`-redirected SQLite/FAISS at call time
- `seeded_tenant` — creates a real dim=8 FAISS index (numpy seed=42, 3 chunks) + real registry row (status=active); patches `vectorstore.retriever.embed_query` to return a compatible dim-8 vector
- `mock_llm` — patches per-node: `graph.nodes.router.grade` → "retrieve", `graph.nodes.doc_grader.grade` → "yes", `graph.nodes.query_rewriter.grade` → rephrased string, `graph.nodes.hallucination_grader.grade` → "0.90", `graph.nodes.answer_grader.grade` → "0.90", `graph.nodes.generator.generate` → canned answer
- `registered_tenant` — calls `/tenants/register` via TestClient and returns `{tenant_id, name, api_key}`

Unit tests (`tests/unit/`):
- `test_router.py` (3) — retrieve/direct_answer decisions, ambiguous defaults to retrieve
- `test_doc_grader.py` (5) — filter irrelevant, pass relevant, partial filter, empty docs, rewritten_query used
- `test_query_rewriter.py` (4) — rewrite_count increments, sets rewritten_query, strips whitespace
- `test_hallucination_grader.py` (5) — float parsing "0.92", low score, "no"→0.0, "yes"→1.0, threshold boundary
- `test_answer_grader.py` (5) — "0.88" passes, "0.30" fails, "yes"→1.0, "no"→0.0, exact threshold
- `test_guardrails_input.py` (26) — all block_codes: QUERY_TOO_SHORT, QUERY_TOO_LONG, INJECTION_DETECTED, PII_DETECTED, OFF_TOPIC; pipeline short-circuit
- `test_guardrails_output.py` (15) — HALLUCINATION_RISK, MISSING_CITATIONS, fallback skip, direct_answer skip
- `test_vectorstore.py` (7) — loader (PyPDFLoader mocked), store (add_chunks/search/remove_doc_chunks), registry CRUD
- `test_tenant_auth.py` (5) — generate_api_key (64-char hex), hash/verify, rotation invalidates old key
- `test_semantic_cache.py` (6 async) — get/set/hit/miss/invalidate/fail-open with AsyncMock Redis
- `test_metrics.py` (4) — Counter increments, guardrail_blocks_total, ingestion_total, fail-safe pattern

Integration tests (`tests/integration/`):
- `test_graph_retrieve_path.py` (5 async) — direct `await rag_graph.ainvoke()` with seeded_tenant + mock_llm; citations, scores, route_decision, rewrite_count=0
- `test_graph_rewrite_path.py` (3 async) — doc_grader rejects first N calls, accepts after; rewrite_count increments
- `test_graph_fallback_path.py` (4 async) — doc_grader always "no" → fallback=True, correct shape, rewrite_count==MAX_REWRITE_ATTEMPTS
- `test_query_endpoint.py` (11) — HTTP TestClient: happy path, unknown tenant 401, wrong key 401, injection 422, off-topic 422, cache hit/miss, rate limit 429, metrics 200
- `test_docs_endpoint.py` (7) — upload 202→active, duplicate 409, list isolation, delete, nonexistent 404, replace bumps version
- `test_tenant_onboarding.py` (5) — storage structure created, duplicate rejected, deactivated 401, key rotation, register→upload→seed FAISS→query→citation check
- `test_multitenant_isolation.py` (5) — header/path mismatch 403, wrong key 401, doc IDs not cross-contaminated, cannot delete other tenant's doc, simultaneous queries succeed

Security tests (`tests/security/`):
- `test_prompt_injection.py` (3) — direct injection 422, indirect quarantine tracking, generator spy
- `test_pii_leakage.py` (6) — SSN/email queries 422, clean query 200, unit-level check_pii blocks
- `test_cross_tenant_isolation.py` (4) — path/header mismatch 403, wrong key 401, cross-doc contamination, delete 403
- `test_rate_limit_enforcement.py` (4) — QPS exceeded 429, within limit 200, token budget 429, fail-open when Redis=None
- `test_key_rotation.py` (3) — old key 401, new key 200, atomicity (new key immediately verifiable)

Eval (`tests/eval/`):
- `run_evals.py` — exits 0 if LANGSMITH_API_KEY unset; exits 1 if hallucination_rate ≥ HALLUCINATION_THRESHOLD or mean_answer_score < ANSWER_SCORE_THRESHOLD; falls back to local eval if LangSmith unreachable
- `ome/eval_dataset.json` — 10 golden Q&A pairs for OME tenant (SNMP alerts, device discovery, firmware, hardware inventory, audit logs, etc.)

**Non-obvious decisions:**
- LLM mock patches must target each node's module namespace (`graph.nodes.router.grade`, not `llm.client.grade`). Nodes do `from llm.client import grade` which creates a local binding; patching the source does not affect already-imported names.
- Rate limit tests require two things together: `app.state.redis = object()` (non-None sentinel to bypass fail-open) AND `monkeypatch.setattr("app.middleware.rate_limiter._check_qps", ...)`. Reset `app.state.redis = None` in a `finally` block.
- `seeded_tenant` FAISS dim=8: small dimension avoids calling the real embeddings API. `embed_query` is monkeypatched to return a compatible dim-8 vector in all integration/security tests that invoke the retriever.
- Integration and security tests use **real SQLite** (via `tmp_storage`). Never mock the database — prior incidents showed mock/prod divergence masked broken migrations.
- `pytest.ini` sets `asyncio_mode = auto` so `async def test_*` functions are collected and run without explicit `@pytest.mark.asyncio` decorators.
- `tests/eval/run_evals.py` `DATASET_PATH` points to `ome/eval_dataset.json` (subdirectory), not the parent `eval/` directory. The subdirectory structure allows multiple tenant-specific golden datasets side by side.

---

### Phase 9 — Next.js Tenant Frontend
**Commit:** `3b29993`

**What was built:**

Backend additions:
- `app/main.py` — `CORSMiddleware` added. Origins controlled by `FRONTEND_ORIGINS` env var (comma-separated, default `http://localhost:3001`). Middleware is added **before** `TenantResolverMiddleware` / `RateLimiterMiddleware` so CORS preflight requests are handled without triggering auth.
- `app/routes/feedback.py` — `POST /{tenant_id}/feedback`. Accepts `{run_id, score, comment}`; calls `langsmith.Client().create_feedback()`. Returns 502 if LangSmith is unreachable — fail-open rather than silently swallowing the error.
- `config/settings.py` — `FRONTEND_ORIGINS: str` field added.
- `docker-compose.yml` — 6-service compose: redis, platform-api, ingestion-worker, prometheus, grafana, frontend (port 3001). `Dockerfile.api` added for the API + worker image.
- `docker/prometheus.yml` — Prometheus scrape config (was missing; required for the grafana service).

Frontend (`frontend/`):
- **Auth:** `sessionStorage` only — clears on tab close. `auth-provider.tsx` is a React context that reads/writes via `lib/auth.ts`. On any `401` the `api-client.ts` fetch wrapper calls `clearCredentials()` and does `window.location.href = "/login"` — handles key rotation gracefully without React routing state.
- **Login probe:** `login/page.tsx` temporarily writes credentials to `sessionStorage` before calling `GET /{tenant}/docs`. If the probe succeeds it calls `login()` (which is a no-op write since they're already set); if it fails it removes them immediately. This avoids duplicating the fetch logic.
- **Upload polling:** `use-poll-doc.ts` uses TanStack Query's `refetchInterval` callback — returns `3000` when `status === "processing"`, `false` otherwise. The `doc-upload.tsx` component watches the polled data and fires a toast + clears `pollingId` when status changes. This approach avoids a `useEffect` polling loop.
- **Query chat:** `use-query-agent.ts` uses a raw `fetch` (not `api.post`) to capture the `X-Run-ID` response header, which TanStack Query's `useMutation` doesn't expose. The run_id is returned alongside the response body as `{ ...data, runId }`.
- **CSP:** `next.config.ts` sets `connect-src 'self' <API_URL>` dynamically from `NEXT_PUBLIC_API_URL`. This means the CSP header is baked at build time — if the API URL changes at runtime in the container, rebuild is required.
- **`"use client"` boundary:** All interactive components are Client Components. Page files under `(app)/` are Server Components (no `"use client"`) — they import and render Client Components. This keeps the auth check in `protected-route.tsx` client-only (sessionStorage is browser-only).

**Non-obvious decisions:**
- `CORS` middleware must be added **before** `TenantResolverMiddleware` in FastAPI (which uses LIFO ordering). Adding it after would mean preflight `OPTIONS` requests hit the tenant resolver, which would reject them with 401/403.
- `sessionStorage` vs `localStorage`: sessionStorage clears on tab close, reducing the XSS blast radius window. Acceptable for internal MVP; the migration path to HttpOnly cookies is clean (swap `lib/auth.ts` and add a `/session` endpoint).
- The `(app)` route group uses parenthesis-folder syntax (Next.js App Router convention). The folder name is excluded from the URL — `/docs` not `/(app)/docs`. The group's `layout.tsx` wraps all protected pages with `<ProtectedRoute>`.
- `X-API-Key` is never logged anywhere in the frontend. The `api-client.ts` error handler reads the response body JSON for `detail`, not the request headers.
