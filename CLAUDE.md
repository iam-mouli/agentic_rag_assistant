# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A multi-tenant Enterprise Knowledge Base Platform enabling any product team to onboard documentation and get an AI knowledge assistant with zero platform-team dependency. The authoritative spec is `agentic-rag-platform-design.md` (v1.2).

**Production baseline:** LangChain + FAISS RAG over 500+ OME docs, 80% reduction in onboarding queries, adopted by 7 teams.

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
pytest tests/unit/                                     # Unit tests
pytest tests/integration/                              # Full graph integration tests
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

### Document Ingestion (`vectorstore/`)

- Async via arq worker → 202 Accepted, client polls for status
- Two-layer storage: SQLite doc registry + FAISS vectors (each chunk carries `doc_id` + `tenant_id`)
- Deletion removes from both FAISS index and SQLite registry atomically

### Request Flow

```
Request → Middleware (tenant validate, rate limit) → Semantic cache check
→ Input guardrails → Graph execution → Output guardrails → Cache populate → Response
```

## API Endpoints

```
POST /tenants/register           # Self-serve onboarding
POST /{tenant}/query             # Query with citations
POST /{tenant}/docs/upload       # Upload doc (202 async)
GET  /{tenant}/docs              # List docs
DELETE /{tenant}/docs/{doc_id}   # Remove doc
POST /{tenant}/feedback          # Thumbs up/down
GET  /health, /health/{tenant}   # Status
GET  /metrics                    # Prometheus scrape
```

## Configuration

Copy `.env.example` to `.env`. Set the API key for your chosen provider plus `PLATFORM_ADMIN_KEY` and Redis connection.

All settings go through `config/settings.py` (Pydantic `BaseSettings`). All numeric thresholds live in `config/constants.py` — change them there, not inline.

## Implementation Phases

The design doc specifies 8 phases. Implement in order:
1. ~~Core graph + LLM + prompts + vectorstore~~ — **Completed**
2. Query REST API + schemas
3. Multi-tenant foundation + quotas + key rotation
4. Per-tenant doc management + async ingestion
5. Guardrails (input + output + indirect injection)
6. Tracing + structured logs
7. Metrics + dashboards + semantic cache
8. Full test suite + security tests

Do not skip ahead — each phase depends on the previous. The design doc is the source of truth for implementation details.
