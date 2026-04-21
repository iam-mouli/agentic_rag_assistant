# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A multi-tenant Enterprise Knowledge Base Platform enabling any product team to onboard documentation and get an AI knowledge assistant with zero platform-team dependency. The authoritative spec is `agentic-rag-platform-design.md` (v1.2).

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

### Guardrails (`guardrails/`) — Phase 5, not yet built

Two-phase, decoupled from graph — update independently:
- **Input:** topic_checker, pii_filter, injection_detector, length_validator
- **Output:** hallucination_gate (≥0.75), citation_enforcer, toxicity_filter, confidence_tagger
- **Injection defense:** chunk-time classifier quarantines flagged content; generator prompt hardened with XML wrapping

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
| 5 | Pending | Guardrails — input + output + indirect injection defense |
| 6 | Pending | Tracing + structured logs (LangSmith, structlog) |
| 7 | Pending | Metrics + dashboards + semantic cache |
| 8 | Pending | Full test suite + security tests |

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

### Phase 5 — Guardrails (Next)

**What to build:**
- `guardrails/input/` — topic_checker, pii_filter, injection_detector, length_validator
- `guardrails/output/` — hallucination_gate, citation_enforcer, toxicity_filter, confidence_tagger
- `guardrails/indirect_injection/` — chunk-time classifier that quarantines flagged content before it enters the FAISS index
- Wire input guardrails into `app/routes/query.py` **before** graph invoke
- Wire output guardrails into `app/routes/query.py` **after** graph invoke
- Generator prompt is already XML-wrapped for injection defense (see `prompts/generator.py`)

**Key constraints from design doc:**
- Guardrails are **decoupled from the graph** — they wrap the graph call at the route layer, not inside nodes
- NeMo Guardrails handles the Rails config; custom validators supplement it
- Injection detector runs at **chunk ingestion time** (`vectorstore/ingestion_worker.py → _ingest_sync`) to quarantine adversarial content before it pollutes the index
