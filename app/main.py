from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.middleware.rate_limiter import RateLimiterMiddleware
from app.middleware.tenant_resolver import TenantResolverMiddleware
from app.routes import health, query, tenants
from config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise tenant registry schema
    from tenants.registry import init_db
    init_db()

    # Compile LangGraph StateGraph on startup (not on first request)
    from graph.builder import rag_graph  # noqa: F401

    # Redis — optional; rate limiter + cache fail open if unavailable
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await client.ping()
        app.state.redis = client
    except Exception:
        app.state.redis = None

    yield

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
