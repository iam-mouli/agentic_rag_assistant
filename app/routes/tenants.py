from fastapi import APIRouter, HTTPException

from app.schemas.request import TenantRegisterRequest, TenantUpdateRequest
from tenants.key_rotation import rotate_key
from tenants.manager import register_tenant
from tenants.registry import deactivate_tenant, get_tenant_by_id, list_tenants, update_tenant

router = APIRouter(prefix="/tenants", tags=["tenants"])

_HIDDEN = {"api_key_hash"}


def _safe(tenant: dict) -> dict:
    return {k: v for k, v in tenant.items() if k not in _HIDDEN}


@router.post("/register", status_code=201)
async def register(request: TenantRegisterRequest):
    try:
        return register_tenant(request.tenant_name, request.team_email)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/")
async def list_all():
    return [_safe(t) for t in list_tenants()]


@router.get("/{tenant_id}")
async def get_one(tenant_id: str):
    tenant = get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return _safe(tenant)


@router.put("/{tenant_id}")
async def update(tenant_id: str, request: TenantUpdateRequest):
    fields = {k: v for k, v in request.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_tenant(tenant_id, **fields)
    return {"tenant_id": tenant_id, **fields}


@router.post("/{tenant_id}/rotate-key")
async def rotate(tenant_id: str):
    result = rotate_key(tenant_id)
    if not result:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return result


@router.delete("/{tenant_id}", status_code=200)
async def deactivate(tenant_id: str):
    deactivate_tenant(tenant_id)
    return {"tenant_id": tenant_id, "status": "deactivated"}
