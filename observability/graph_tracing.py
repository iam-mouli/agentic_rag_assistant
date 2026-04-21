"""Wraps LangGraph node callables to emit structured entry/exit logs with latency."""
import time
from typing import Callable

from observability.logging.structured_logger import get_logger

logger = get_logger(__name__)


def traced_node(name: str, fn: Callable) -> Callable:
    """Return a wrapper around *fn* that logs entry and exit with latency_ms."""

    def _wrapper(state):
        tenant_id = state.get("tenant_id", "unknown")
        logger.debug("graph_node_enter", node=name, tenant_id=tenant_id)
        t0 = time.monotonic()
        try:
            result = fn(state)
            latency_ms = round((time.monotonic() - t0) * 1000, 1)
            logger.debug("graph_node_exit", node=name, tenant_id=tenant_id, latency_ms=latency_ms)
            return result
        except Exception as exc:
            latency_ms = round((time.monotonic() - t0) * 1000, 1)
            logger.error(
                "graph_node_error",
                node=name,
                tenant_id=tenant_id,
                latency_ms=latency_ms,
                error=str(exc),
            )
            raise

    _wrapper.__name__ = fn.__name__
    _wrapper.__qualname__ = fn.__qualname__
    return _wrapper
