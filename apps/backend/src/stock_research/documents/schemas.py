import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    version_id: uuid.UUID
    version_no: int
    document_type: str | None
    content_hash: str
    raw_object_key: str
    status: str
    created_at: datetime


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    owner_id: uuid.UUID | None
    symbol: str | None
    document_type: str | None
    content_hash: str | None
    status: str
    source_level: str | None
    external_model_allowed: bool
    created_at: datetime
    updated_at: datetime
