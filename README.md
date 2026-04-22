# agentic-rag-platform

A **multi-tenant, self-serve Enterprise Knowledge Base Platform** built on LangGraph. Any product team can onboard their documentation and get a self-correcting AI knowledge assistant — with zero platform-team dependency.

**Origin:** First deployed as the OME (OpenManage Enterprise) knowledge assistant — 80% reduction in new-engineer onboarding queries, adopted by 7 teams, 500+ documents indexed. This platform generalises that to any product line.

---

## How It Works

Queries flow through a stateful LangGraph agent that retrieves, grades, and self-corrects before answering:

```
Router → Retriever → DocGrader → Generator → HallucinationGrader → AnswerGrader → END
                         ↓ (all chunks fail grading)
                    QueryRewriter → back to Retriever  (max 3 rewrites → Fallback)
```

- **Router** decides whether the query needs document retrieval or can be answered directly
- **DocGrader** filters irrelevant chunks before generation — prevents garbage-in/garbage-out
- **Self-correction loop** rewrites the query and retries when retrieval quality is poor (capped at 3 attempts)
- **HallucinationGrader** verifies the answer is grounded in the retrieved documents
- **AnswerGrader** verifies the answer actually addresses the question
- Every answer carries `citations` (doc_id, filename, page) so the source is always traceable

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent Framework | LangGraph |
| LLMs | OpenAI / Anthropic / Gemini — switch via `LLM_PROVIDER` env var |
| Embeddings | OpenAI / Gemini — switch via `EMBEDDING_PROVIDER` env var |
| Vector Store | FAISS (per-tenant, isolated) |
| API | FastAPI + Pydantic |
| Task Queue | arq (Redis-backed async ingestion) |
| Cache | Redis (semantic cache + rate limits + FAISS write locks) |
| DB | SQLite (dev) / PostgreSQL (prod) |
| Tracing | LangSmith |
| Metrics | Prometheus + Grafana |
| Logging | structlog (JSON) |
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind CSS + shadcn/ui + TanStack Query |

---

## Quickstart

### 1. Install dependencies

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` — minimum required fields:

```bash
LLM_PROVIDER=openai            # openai | anthropic | gemini
EMBEDDING_PROVIDER=openai      # openai | gemini

OPENAI_API_KEY=sk-...          # or ANTHROPIC_API_KEY / GOOGLE_API_KEY
PLATFORM_ADMIN_KEY=your-secret-admin-key
```

All other fields have sensible defaults for local development.

### 3. Start the API

```bash
uvicorn app.main:app --reload
```

API is now available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### 4. (Optional) Start the async ingestion worker

Required in production for large document uploads. In dev, ingestion runs synchronously without it.

```bash
arq vectorstore.ingestion_worker.WorkerSettings
```

### 5. (Optional) Full stack with Prometheus + Grafana + Frontend

```bash
docker-compose up --build
```

| Service | URL |
|---|---|
| Platform API | http://localhost:8000 |
| Frontend UI | http://localhost:3001 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (admin/admin) |

### 6. (Optional) Frontend dev server only

```bash
cd frontend
cp .env.example .env.local   # set NEXT_PUBLIC_API_URL if API is not on :8000
npm install
npm run dev                  # http://localhost:3001
```

---

## Using the Platform

### Step 1 — Register a tenant

Each product team is a tenant. Registration is a one-time admin operation.

```bash
curl -X POST http://localhost:8000/tenants/register \
  -H "X-Platform-Admin-Key: your-secret-admin-key" \
  -H "Content-Type: application/json" \
  -d '{"tenant_name": "ome", "team_email": "ome-team@example.com"}'
```

Response — **save the `api_key`, it is shown only once**:

```json
{
  "tenant_id": "a1b2c3d4-...",
  "tenant_name": "ome",
  "api_key": "7f3a9c..."
}
```

### Step 2 — Upload documents

Upload PDF documentation for the tenant. Returns `202 Accepted` immediately; ingestion runs asynchronously.

```bash
curl -X POST http://localhost:8000/ome/docs/upload \
  -H "X-Tenant-ID: ome" \
  -H "X-API-Key: 7f3a9c..." \
  -F "file=@OME_UserGuide_v4.pdf"
```

```json
{ "doc_id": "d001", "filename": "OME_UserGuide_v4.pdf", "status": "processing" }
```

Poll until active:

```bash
curl http://localhost:8000/ome/docs/d001 \
  -H "X-Tenant-ID: ome" -H "X-API-Key: 7f3a9c..."
```

```json
{ "doc_id": "d001", "status": "active", "chunk_count": 142, "pages": 38 }
```

### Step 3 — Query

```bash
curl -X POST http://localhost:8000/ome/query \
  -H "X-Tenant-ID: ome" \
  -H "X-API-Key: 7f3a9c..." \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I configure SNMP alert destinations?"}'
```

```json
{
  "answer": "SNMP alert destinations can be configured in OME by navigating to Alerts > Alert Destinations...",
  "confidence": 0.91,
  "confidence_level": "high",
  "fallback": false,
  "cache": false,
  "citations": [
    {
      "doc_id": "d001",
      "filename": "OME_UserGuide_v4.pdf",
      "page": 142,
      "chunk_preview": "Alert configuration is accessible under..."
    }
  ]
}
```

### Managing documents

```bash
# List all documents for a tenant
curl http://localhost:8000/ome/docs \
  -H "X-Tenant-ID: ome" -H "X-API-Key: 7f3a9c..."

# Replace a document with a new version
curl -X PUT http://localhost:8000/ome/docs/d001 \
  -H "X-Tenant-ID: ome" -H "X-API-Key: 7f3a9c..." \
  -F "file=@OME_UserGuide_v5.pdf"

# Remove a document
curl -X DELETE http://localhost:8000/ome/docs/d001 \
  -H "X-Tenant-ID: ome" -H "X-API-Key: 7f3a9c..."
```

### Rotating an API key

Old key is invalidated immediately. New key is returned once — store it securely.

```bash
curl -X POST http://localhost:8000/tenants/a1b2c3d4-.../rotate-key \
  -H "X-Platform-Admin-Key: your-secret-admin-key"
```

### Submitting feedback

```bash
curl -X POST http://localhost:8000/ome/feedback \
  -H "X-Tenant-ID: ome" -H "X-API-Key: 7f3a9c..." \
  -H "Content-Type: application/json" \
  -d '{"run_id": "<X-Run-ID from query response header>", "score": 1, "comment": "Very helpful"}'
```

---

## API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/tenants/register` | Admin key | Register a new tenant |
| `GET` | `/tenants` | Admin key | List all tenants |
| `GET` | `/tenants/{tenant_id}` | Admin key | Tenant detail + status |
| `PUT` | `/tenants/{tenant_id}` | Admin key | Update quotas / metadata |
| `POST` | `/tenants/{tenant_id}/rotate-key` | Admin key | Rotate API key |
| `DELETE` | `/tenants/{tenant_id}` | Admin key | Deactivate tenant |
| `POST` | `/{tenant_id}/query` | Tenant key | Query with citations |
| `POST` | `/{tenant_id}/docs/upload` | Tenant key | Upload document (202 async) |
| `GET` | `/{tenant_id}/docs` | Tenant key | List indexed documents |
| `GET` | `/{tenant_id}/docs/{doc_id}` | Tenant key | Document metadata + status |
| `PUT` | `/{tenant_id}/docs/{doc_id}` | Tenant key | Replace document (new version) |
| `DELETE` | `/{tenant_id}/docs/{doc_id}` | Tenant key | Remove document |
| `POST` | `/{tenant_id}/feedback` | Tenant key | Submit thumbs up/down |
| `GET` | `/health` | None | Platform liveness |
| `GET` | `/health/{tenant_id}` | None | Per-tenant health |
| `GET` | `/metrics` | None | Prometheus scrape endpoint |

All tenant endpoints require both headers:

```
X-Tenant-ID: <tenant_name>
X-API-Key: <issued_api_key>
```

### Error responses

| Status | Meaning |
|---|---|
| `401` | Invalid or missing API key |
| `403` | Tenant ID in header does not match URL path |
| `409` | Duplicate document (same SHA-256 hash already indexed) |
| `422` | Guardrail block — body contains `{ "code": "INJECTION_DETECTED" \| "PII_DETECTED" \| "OFF_TOPIC" \| ... }` |
| `429` | Rate limit — `X-Quota-Exceeded: qps \| monthly_tokens`; `Retry-After` header present |

---

## LLM Provider Selection

Switch provider via environment variable — no code changes required.

| `LLM_PROVIDER` | Generation model | Grader model |
|---|---|---|
| `openai` (default) | `gpt-4o` | `gpt-4o-mini` |
| `anthropic` | `claude-sonnet-4-6` | `claude-haiku-4-5-20251001` |
| `gemini` | `gemini-2.0-flash` | `gemini-2.0-flash-lite` |

`EMBEDDING_PROVIDER` is independent (`openai` or `gemini` — Anthropic has no embedding model).

---

## Multi-Tenancy

Each tenant is fully isolated:

```
storage/tenants/
├── ome/
│   ├── docs/          ← uploaded PDFs
│   ├── faiss_index/   ← FAISS vectors
│   └── registry.db    ← document metadata
├── idrac/
│   └── ...
└── {any-team}/        ← auto-created on registration
```

**Quotas** (configurable per tenant via `PUT /tenants/{id}`):

| Limit | Default |
|---|---|
| QPS | 10 queries/second |
| Monthly token budget | 5,000,000 tokens |

Exceeding either returns `429` with the appropriate `X-Quota-Exceeded` header.

---

## Guardrails

**Input** (evaluated before the graph, short-circuits on first failure):

| Check | Block code |
|---|---|
| Query too short / too long (3–500 chars) | `QUERY_TOO_SHORT` / `QUERY_TOO_LONG` |
| Prompt injection patterns | `INJECTION_DETECTED` |
| PII detected (SSN, credit card, email, phone) | `PII_DETECTED` |
| Query outside enterprise/tech domain | `OFF_TOPIC` |

**Output** (evaluated after generation):

| Check | Effect |
|---|---|
| Hallucination score < 0.75 | `HALLUCINATION_RISK` — answer blocked |
| RAG answer with no citations | `MISSING_CITATIONS` — answer blocked |
| Toxic content in generation | Answer blocked |
| Answer score → confidence label | `high` ≥ 0.85 / `medium` ≥ 0.70 / `low` otherwise |

**Indirect injection defense:** chunks are scanned at upload time; adversarial chunks are quarantined before reaching FAISS. The generator prompt wraps retrieved content in XML delimiters to prevent embedded instructions from executing.

---

## Observability

- **LangSmith** — full agent traces per query (node inputs/outputs, latencies, token usage); opt-in via `LANGSMITH_API_KEY`
- **Prometheus** — `/metrics` endpoint; labeled by `tenant_id`; counters for queries, guardrail blocks, ingestion, cache hits; histograms for latency and hallucination score
- **Grafana** — two pre-built dashboards in `docker/grafana/`: platform-wide overview and per-tenant drilldown
- **Structured logs** — JSON via structlog; every request binds `request_id` + `tenant_id` as context vars so all log lines (including deep inside nodes) carry both fields automatically
- **Response header** — `X-Run-ID` carries the LangSmith trace UUID when tracing is enabled

---

## Running Tests

```bash
# Unit tests (mocked LLM/Redis/FAISS)
pytest tests/unit/

# Integration tests (real SQLite, mocked LLM)
pytest tests/integration/

# Security tests
pytest tests/security/

# Single test
pytest tests/unit/test_router.py::test_router_decides_retrieve

# LangSmith evals (CI-gated — requires LANGSMITH_API_KEY)
python tests/eval/run_evals.py
```

`run_evals.py` exits `0` if `LANGSMITH_API_KEY` is unset (graceful skip in local dev). In CI it exits `1` if `hallucination_rate >= 0.75` or `mean_answer_score < 0.70`.

---

## Configuration Reference

All thresholds live in `config/constants.py` — change them there, not inline:

| Constant | Default | Effect |
|---|---|---|
| `MAX_REWRITE_ATTEMPTS` | `3` | Max query rewrites before fallback |
| `HALLUCINATION_THRESHOLD` | `0.75` | Minimum grounding score to pass |
| `ANSWER_SCORE_THRESHOLD` | `0.70` | Minimum answer relevance to pass |
| `TOP_K_RETRIEVAL` | `5` | Chunks retrieved per query |
| `CHUNK_SIZE` | `1000` | Characters per chunk |
| `SEMANTIC_CACHE_SIMILARITY_THRESHOLD` | `0.95` | Cosine similarity for cache hit |
| `DEFAULT_TENANT_QPS_LIMIT` | `10` | Queries per second per tenant |
| `DEFAULT_MONTHLY_TOKEN_BUDGET` | `5_000_000` | Tokens per tenant per month |

---

## Frontend (Phase 9)

A self-serve tenant UI is available at `http://localhost:3001` when running via docker-compose or the frontend dev server.

**Flows:**
- **Login** — paste `tenant_id` + `api_key`; credentials stored in `sessionStorage`, cleared on tab close or logout
- **Documents** — drag-and-drop PDF upload with real-time polling (`processing → active`), document list with status badges, and one-click deletion
- **Query** — chat-style UI with answer confidence badge, citation cards (filename + page + preview), and thumbs-up/down feedback wired to LangSmith traces
- **Settings** — tenant info readout, key-rotation help text, logout

**Security notes:**
- API key lives in `sessionStorage` — XSS-risky but acceptable for an internal Dell tool at MVP stage; HttpOnly session cookies are the recommended follow-up
- Strict CSP headers set in `next.config.ts`; `X-API-Key` is never logged
- On `401`, the auth provider wipes credentials and redirects to `/login`

## Project Structure

```
agentic-rag-platform/
├── app/                    # FastAPI — routes, middleware, schemas
├── graph/                  # LangGraph agent — nodes, edges, state
├── guardrails/             # Input + output safety validators
├── observability/          # LangSmith tracing, Prometheus metrics, structlog
├── tenants/                # Tenant lifecycle — registry, auth, key rotation
├── vectorstore/            # FAISS operations, doc registry, ingestion worker
├── llm/                    # Provider-agnostic LLM client factory
├── prompts/                # All prompt templates (centralized)
├── cache/                  # Redis semantic cache
├── config/                 # Settings (Pydantic BaseSettings) + constants
├── docker/                 # Grafana dashboards + Prometheus config
├── frontend/               # Next.js 14 tenant UI (Phase 9)
├── tests/                  # Unit, integration, security, eval
├── docker-compose.yml
├── Dockerfile.api
├── .env.example
└── requirements.txt
```

---

---

## Implementation Phases

| Phase | Deliverable | Status |
|---|---|---|
| 1 | Core graph + LLM + prompts + vectorstore | ✅ Done |
| 2 | Query REST API + schemas | ✅ Done |
| 3 | Multi-tenant foundation + quotas + key rotation | ✅ Done |
| 4 | Per-tenant doc management + async ingestion | ✅ Done |
| 5 | Guardrails (input + output + indirect injection) | ✅ Done |
| 6 | Tracing + structured logs | ✅ Done |
| 7 | Metrics + dashboards + semantic cache | ✅ Done |
| 8 | Full test suite + security tests | ✅ Done |
| 9 | Frontend — Next.js tenant UI + CORS middleware | ✅ Done |

*Chandiramouli Ravisankar — April 2026*
