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
    fallback: bool
    citations: List[Citation]
    cache: bool = False  # True when served from semantic cache (Phase 7)
