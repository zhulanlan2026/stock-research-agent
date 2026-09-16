from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.auth.dependencies import get_current_user
from stock_research.core.config import get_settings
from stock_research.iam.dependencies import require_permission
from stock_research.review.human_review import HumanReviewService
from stock_research.review.schemas import ReviewResponse
from stock_research.stores.models.iam import User
from stock_research.stores.session import get_session
from stock_research.supply_chain.neo4j_client import Neo4jPublisher
from stock_research.supply_chain.schemas import (
    GraphEdgeResponse,
    GraphResponse,
    SupplyChainReviewRequest,
)

router = APIRouter(prefix="/supply-chain", tags=["supply-chain"])
_require_review = require_permission("report.review")


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


@router.post(
    "/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_supply_chain_review(
    body: SupplyChainReviewRequest,
    current_user: User = Depends(_require_review),
    session: AsyncSession = Depends(get_session),
) -> ReviewResponse:
    review = await HumanReviewService(session).create(
        tenant_id=current_user.tenant_id,
        target_type="supply_chain_graph",
        target_id=body.symbol or "graph",
        reviewer_id=current_user.id,
    )
    await session.commit()
    return ReviewResponse.model_validate(review)
