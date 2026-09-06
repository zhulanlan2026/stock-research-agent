from fastapi import APIRouter, Depends

from stock_research.auth.dependencies import get_current_user
from stock_research.core.config import get_settings
from stock_research.stores.models.iam import User
from stock_research.supply_chain.neo4j_client import Neo4jPublisher
from stock_research.supply_chain.schemas import GraphEdgeResponse, GraphResponse

router = APIRouter(prefix="/supply-chain", tags=["supply-chain"])


@router.get("/graph", response_model=GraphResponse)
async def get_graph(
    _: User = Depends(get_current_user),
) -> GraphResponse:
    settings = get_settings()
    try:
        publisher = Neo4jPublisher(
            settings.neo4j_uri,
            settings.neo4j_user,
            settings.neo4j_password,
        )
        try:
            data = publisher.list_graph()
        finally:
            publisher.close()
    except Exception:
        return GraphResponse(nodes=[], edges=[])

    return GraphResponse(
        nodes=data.nodes,
        edges=[
            GraphEdgeResponse(source=source, predicate=predicate, target=target)
            for source, predicate, target in data.edges
        ],
    )
