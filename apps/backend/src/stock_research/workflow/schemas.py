import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TaskCreateRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    mode: str = Field(pattern="^(quick|standard|deep)$")
    as_of: datetime | None = None
    modules: list[str] = Field(default_factory=list)
    question: str | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    task_type: str
    status: str
    symbol: str
    mode: str
    as_of: datetime | None
    requested_modules: list[str]
    question: str | None
    created_at: datetime
    updated_at: datetime


class TaskVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    version_no: int
    payload: dict[str, object]


class ReportRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    mode: str = Field(pattern="^(quick|standard|deep)$", default="standard")
    as_of: datetime | None = None


class ReportSectionResponse(BaseModel):
    title: str
    data: dict[str, object]


class ReportResponse(BaseModel):
    symbol: str
    as_of: datetime
    module_version: str
    summary: str
    sections: list[ReportSectionResponse]
