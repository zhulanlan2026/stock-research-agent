from typing import Any

import pytest

from stock_research.review.human_review import HumanReviewService


async def test_human_review_service_creates_and_decides(db_context: Any) -> None:
    async with db_context.factory() as session:
        service = HumanReviewService(session)
        review = await service.create(
            tenant_id=db_context.tenant_id,
            target_type="report",
            target_id="report-1",
            reviewer_id=db_context.user_id,
        )
        event = await service.decide(review, "APPROVED", comment="通过")
        await session.commit()

        assert review.status == "APPROVED"
        assert event.to_status == "APPROVED"


async def test_human_review_service_rejects_invalid_decision(db_context: Any) -> None:
    async with db_context.factory() as session:
        service = HumanReviewService(session)
        review = await service.create(
            tenant_id=db_context.tenant_id,
            target_type="report",
            target_id="report-1",
        )
        await session.commit()

        with pytest.raises(ValueError):
            await service.decide(review, "MAYBE")
