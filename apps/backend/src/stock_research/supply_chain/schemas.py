import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class GraphEdgeResponse(BaseModel):
    source: str
    predicate: str
    target: str


class GraphResponse(BaseModel):
    nodes: list[str]
    edges: list[GraphEdgeResponse]


class SupplyChainReviewRequest(BaseModel):
    symbol: str | None = Field(default=None, max_length=32)


class SupplyChainContractCreate(BaseModel):
    subject_org: str = Field(..., min_length=1, max_length=200)
    object_org: str = Field(..., min_length=1, max_length=200)
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(..., min_length=1, max_length=8)
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class SupplyChainContractResponse(BaseModel):
    id: uuid.UUID
    subject_org: str
    object_org: str
    amount: Decimal
    currency: str
    valid_from: datetime | None
    valid_to: datetime | None
    status: str
    evidence_ids: list[str]


class OrganizationAliasCreate(BaseModel):
    canonical_name: str = Field(..., min_length=1, max_length=200)
    alias: str = Field(..., min_length=1, max_length=200)


class OrganizationAliasResponse(BaseModel):
    id: uuid.UUID
    canonical_name: str
    alias: str


class RiskPropagationRequest(BaseModel):
    initial_risk: dict[str, float] = Field(..., min_length=1)
    max_steps: int = Field(default=1, ge=1, le=100)
    damping: float = Field(default=0.5, ge=0, le=1)


class RiskPropagationResponse(BaseModel):
    risk: dict[str, float]


class SymbolResolveResponse(BaseModel):
    symbol: str
    organization: str


class RiskSnapshotCreate(BaseModel):
    symbol: str | None = Field(default=None, max_length=32)
    initial_risk: dict[str, float] = Field(..., min_length=1)
    max_steps: int = Field(default=1, ge=1, le=100)
    damping: float = Field(default=0.5, ge=0, le=1)


class RiskSnapshotResponse(BaseModel):
    id: uuid.UUID
    symbol: str | None
    initial_risk: dict[str, float]
    max_steps: int
    damping: float
    result: dict[str, float]
    created_at: datetime
