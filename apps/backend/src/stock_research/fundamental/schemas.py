import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class FinancialFactCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    metric: str = Field(min_length=1, max_length=100)
    period: str = Field(min_length=1, max_length=32)
    value: Decimal
    unit: str = Field(min_length=1, max_length=32)
    source_id: str = Field(min_length=1, max_length=200)
    disclosed_at: datetime
    available_at: datetime
    revision_no: int = Field(default=1, ge=1)
    truth_status: str = Field(default="VERIFIED", min_length=1, max_length=32)
    tenant_id: uuid.UUID | None = None
    fact_metadata: dict[str, object] = Field(default_factory=dict)


class FinancialFactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    symbol: str
    metric: str
    period: str
    value: Decimal
    unit: str
    source_id: str
    disclosed_at: datetime
    available_at: datetime
    revision_no: int
    truth_status: str
    fact_metadata: dict[str, object]
    created_at: datetime
    updated_at: datetime
