from typing import List, Optional

from pydantic import BaseModel


class Citation(BaseModel):
    doc_id: Optional[str] = None
    filename: Optional[str] = None
    page: Optional[int] = None
    chunk_preview: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    confidence: float
    confidence_level: str = "low"  # "high" | "medium" | "low"
    fallback: bool
    citations: List[Citation]
    cache: bool = False  # True when served from semantic cache (Phase 7)


class TenantResponse(BaseModel):
    tenant_id: str
    name: str
    team_email: str
    status: str
    created_at: str
    doc_count: int
    qps_limit: int
    monthly_token_budget: int
    tokens_used_month: int
    api_key_version: int
