from pydantic import BaseModel


class GraphEdgeResponse(BaseModel):
    source: str
    predicate: str
    target: str


class GraphResponse(BaseModel):
    nodes: list[str]
    edges: list[GraphEdgeResponse]
