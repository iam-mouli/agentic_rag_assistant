from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.middleware.rate_limiter import RateLimiterMiddleware
from app.middleware.tenant_resolver import TenantResolverMiddleware
from app.routes import docs, health, query, tenants
from config.settings import settings
from observability.logging.structured_logger import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise tenant registry schema
    from tenants.registry import init_db
    init_db()

    # Compile LangGraph StateGraph on startup (not on first request)
    from graph.builder import rag_graph  # noqa: F401

    # Redis — optional; rate limiter + arq pool fail open if unavailable
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await client.ping()
        app.state.redis = client
    except Exception:
        app.state.redis = None

    # arq pool — optional; doc ingestion falls back to sync if unavailable
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        app.state.arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    except Exception:
        app.state.arq_pool = None

    yield

    if getattr(app.state, "arq_pool", None):
        await app.state.arq_pool.aclose()
    if getattr(app.state, "redis", None):
        await app.state.redis.aclose()


app = FastAPI(
    title="agentic-rag-platform",
    version="0.1.0",
    description="Multi-tenant agentic RAG platform with self-correcting retrieval",
    lifespan=lifespan,
)

# Middleware runs in reverse-add order: TenantResolver (added last) runs first,
# then RateLimiter reads request.state.tenant set by TenantResolver.
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(TenantResolverMiddleware)

app.include_router(health.router)
app.include_router(query.router)
app.include_router(tenants.router)
app.include_router(docs.router)


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
