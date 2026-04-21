import asyncio

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from config.settings import settings
from tenants.auth import verify_api_key
from tenants.registry import get_tenant_by_name

_PUBLIC_PATHS = {"/health", "/openapi.json"}
_PUBLIC_PREFIXES = ("/docs", "/redoc")
_ADMIN_PREFIX = "/tenants"


def _is_public(path: str) -> bool:
    return path in _PUBLIC_PATHS or any(path.startswith(p) for p in _PUBLIC_PREFIXES)


class TenantResolverMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if _is_public(path):
            return await call_next(request)

        # Admin routes — protected by platform admin key
        if path.startswith(_ADMIN_PREFIX):
            admin_key = request.headers.get("X-Platform-Admin-Key", "")
            if admin_key != settings.PLATFORM_ADMIN_KEY:
                return JSONResponse(
                    {"detail": "Invalid or missing X-Platform-Admin-Key"},
                    status_code=401,
                )
            return await call_next(request)

        # Tenant routes — require X-Tenant-ID + X-API-Key
        tenant_header = request.headers.get("X-Tenant-ID", "")
        api_key = request.headers.get("X-API-Key", "")

        if not tenant_header or not api_key:
            return JSONResponse(
                {"detail": "X-Tenant-ID and X-API-Key headers are required"},
                status_code=401,
            )

        # Guard against cross-tenant path manipulation (e.g. header=ome, path=/idrac/query)
        path_tenant = path.strip("/").split("/")[0]
        if path_tenant != tenant_header:
            return JSONResponse(
                {"detail": "X-Tenant-ID header does not match URL tenant"},
                status_code=403,
            )

        loop = asyncio.get_event_loop()
        tenant = await loop.run_in_executor(None, get_tenant_by_name, tenant_header)

        if not tenant or tenant["status"] != "active":
            return JSONResponse(
                {"detail": "Unknown or inactive tenant"},
                status_code=401,
            )

        if not await loop.run_in_executor(None, verify_api_key, api_key, tenant["api_key_hash"]):
            return JSONResponse({"detail": "Invalid API key"}, status_code=401)

        request.state.tenant = tenant
        return await call_next(request)
