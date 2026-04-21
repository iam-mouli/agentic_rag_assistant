import datetime
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant = getattr(request.state, "tenant", None)
        if tenant is None:
            return await call_next(request)

        redis = getattr(request.app.state, "redis", None)
        if redis is None:
            # Redis unavailable — fail open, rate limiting skipped
            return await call_next(request)

        # QPS sliding-window check
        allowed, retry_after = await _check_qps(redis, tenant["tenant_id"], tenant["qps_limit"])
        if not allowed:
            return JSONResponse(
                {"detail": "QPS limit exceeded"},
                status_code=429,
                headers={"Retry-After": str(retry_after), "X-Quota-Exceeded": "qps"},
            )

        # Monthly token budget check — only for query endpoints
        if request.url.path.endswith("/query"):
            if tenant["tokens_used_month"] >= tenant["monthly_token_budget"]:
                return JSONResponse(
                    {"detail": "Monthly token budget exceeded"},
                    status_code=429,
                    headers={
                        "Retry-After": str(_seconds_until_month_reset()),
                        "X-Quota-Exceeded": "monthly_tokens",
                    },
                )

        return await call_next(request)


async def _check_qps(redis, tenant_id: str, qps_limit: int) -> tuple[bool, int]:
    now = time.time()
    key = f"qps:{tenant_id}"
    try:
        async with redis.pipeline() as pipe:
            pipe.zadd(key, {str(now): now})
            pipe.zremrangebyscore(key, 0, now - 1.0)
            pipe.zcard(key)
            pipe.expire(key, 2)
            results = await pipe.execute()
        return results[2] <= qps_limit, 1
    except Exception:
        return True, 0  # Fail open on Redis errors


def _seconds_until_month_reset() -> int:
    now = datetime.datetime.now()
    if now.month == 12:
        next_month = datetime.datetime(now.year + 1, 1, 1)
    else:
        next_month = datetime.datetime(now.year, now.month + 1, 1)
    return max(1, int((next_month - now).total_seconds()))
