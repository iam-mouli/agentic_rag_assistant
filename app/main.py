from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routes import health, query


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Compile the LangGraph StateGraph on startup rather than on the first request
    from graph.builder import rag_graph  # noqa: F401
    yield


app = FastAPI(
    title="agentic-rag-platform",
    version="0.1.0",
    description="Multi-tenant agentic RAG platform with self-correcting retrieval",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(query.router)
