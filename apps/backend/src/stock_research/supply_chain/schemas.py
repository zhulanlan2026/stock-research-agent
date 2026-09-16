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
