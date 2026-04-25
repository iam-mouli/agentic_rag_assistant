"""LangSmith run tracking for graph invocations. Opt-in via LANGSMITH_API_KEY."""
import os
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from config.settings import settings
from observability.logging.structured_logger import get_logger

logger = get_logger(__name__)


def _langsmith_enabled() -> bool:
    return bool(settings.LANGSMITH_API_KEY)


def _ensure_env() -> None:
    """Push keys into env vars that the LangSmith SDK reads."""
    if settings.LANGSMITH_API_KEY:
        os.environ.setdefault("LANGCHAIN_API_KEY", settings.LANGSMITH_API_KEY)
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        os.environ.setdefault("LANGCHAIN_PROJECT", settings.LANGSMITH_PROJECT)


@asynccontextmanager
async def trace_graph_run(
    tenant_id: str,
    query: str,
) -> AsyncGenerator[dict, None]:
    """Context manager that opens a LangSmith run and yields a metadata carrier.

    The caller stores graph result metadata into the carrier dict; the manager
    annotates the run on exit.

    If LANGSMITH_API_KEY is absent the context manager is a no-op and yields
    an empty dict so call-sites need no conditional logic.
    """
    run_id = str(uuid.uuid4())
    carrier: dict = {"run_id": run_id}

    if not _langsmith_enabled():
        yield carrier
        return

    _ensure_env()

    try:
        from langsmith import Client
        from langsmith.run_helpers import traceable  # noqa: F401
    except ImportError:
        logger.warning("langsmith_not_installed", reason="pip install langsmith to enable tracing")
        yield carrier
        return

    client = Client(api_key=settings.LANGSMITH_API_KEY)

    try:
        client.create_run(
            id=run_id,
            name="rag_graph_invocation",
            run_type="chain",
            inputs={"query": query, "tenant_id": tenant_id},
            project_name=settings.LANGSMITH_PROJECT,
        )
    except Exception as exc:
        logger.warning("langsmith_create_run_failed", error=str(exc))
        yield carrier
        return

    try:
        yield carrier
    finally:
        metadata = {
            "tenant_id": tenant_id,
            "query_type": carrier.get("route_decision", "unknown"),
            "rewrite_count": carrier.get("rewrite_count", 0),
            "hallucination_score": carrier.get("hallucination_score"),
            "answer_score": carrier.get("answer_score"),
            "fallback": carrier.get("fallback", False),
        }
        try:
            client.update_run(
                run_id,
                outputs={"generation": carrier.get("generation", "")},
                extra={"metadata": metadata},
                end_time=None,
            )
        except Exception as exc:
            logger.warning("langsmith_update_run_failed", error=str(exc), run_id=run_id)


def populate_carrier(carrier: dict, result: dict) -> None:
    """Copy relevant graph result fields into the LangSmith carrier."""
    for key in (
        "generation",
        "route_decision",
        "rewrite_count",
        "hallucination_score",
        "answer_score",
        "fallback",
    ):
        if key in result:
            carrier[key] = result[key]


def get_run_id(carrier: dict) -> Optional[str]:
    return carrier.get("run_id")
