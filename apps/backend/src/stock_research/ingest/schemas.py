from pydantic import BaseModel, Field


class IngestEvent(BaseModel):
    event_id: str = Field(min_length=1, max_length=200)
    event_type: str = Field(min_length=1, max_length=100)
    payload: dict[str, object] = Field(default_factory=dict)


class IngestBatchRequest(BaseModel):
    events: list[IngestEvent] = Field(min_length=1, max_length=100)


class IngestBatchResponse(BaseModel):
    accepted: int
    duplicates: int
