from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.core.config import get_settings
from stock_research.stores.models.review import HumanReview
from stock_research.supply_chain.neo4j_client import Neo4jPublisher
from stock_research.supply_chain.neo4j_rebuild import Neo4jRebuildService


async def apply_supply_chain_review_decision(
    session: AsyncSession,
    review: HumanReview,
    decision: str,
) -> None:
    if review.target_type != "supply_chain_graph" or decision != "APPROVED":
        return

    settings = get_settings()
    publisher = Neo4jPublisher(
        settings.neo4j_uri,
        settings.neo4j_user,
        settings.neo4j_password,
    )
    try:
        await Neo4jRebuildService(session, publisher).rebuild()
    finally:
        publisher.close()
