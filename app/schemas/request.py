from pydantic import BaseModel, Field

from config.constants import MAX_QUERY_LENGTH, MIN_QUERY_LENGTH


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=MIN_QUERY_LENGTH, max_length=MAX_QUERY_LENGTH)


class TenantRegisterRequest(BaseModel):
    tenant_name: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z0-9_-]+$")
    team_email: str


class TenantUpdateRequest(BaseModel):
    qps_limit: int | None = Field(None, ge=1, le=1000)
    monthly_token_budget: int | None = Field(None, ge=100_000)
