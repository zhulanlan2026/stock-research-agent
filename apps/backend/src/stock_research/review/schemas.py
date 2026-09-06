import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    target_type: str
    target_id: str
    status: str
    decision: str | None
    created_at: datetime


class ReviewDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(APPROVED|NEEDS_REVISION|REJECTED)$")
    comment: str | None = None
    reason_code: str | None = None
