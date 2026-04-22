from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["feedback"])


class FeedbackRequest(BaseModel):
    run_id: str = Field(..., description="X-Run-ID from the query response header")
    score: int = Field(..., ge=-1, le=1, description="1 = thumbs up, -1 = thumbs down")
    comment: Optional[str] = Field(None, max_length=500)


@router.post("/{tenant_id}/feedback", status_code=200)
async def submit_feedback(tenant_id: str, body: FeedbackRequest):
    try:
        from langsmith import Client

        client = Client()
        client.create_feedback(
            run_id=body.run_id,
            key="user_score",
            score=body.score,
            comment=body.comment or "",
        )
        return {"status": "recorded", "run_id": body.run_id, "score": body.score}
    except Exception as exc:
        # LangSmith unavailable or run_id invalid — log and fail open so the UI
        # doesn't surface a confusing error for a non-critical action.
        raise HTTPException(
            status_code=502,
            detail=f"Could not record feedback: {exc}",
        ) from exc
