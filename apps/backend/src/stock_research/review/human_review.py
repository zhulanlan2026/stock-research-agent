from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.stores.models.review import HumanReview, HumanReviewEvent

VALID_DECISIONS = {"APPROVED", "NEEDS_REVISION", "REJECTED"}


class HumanReviewService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        tenant_id: uuid.UUID | None,
        target_type: str,
        target_id: str,
        reviewer_id: uuid.UUID | None = None,
    ) -> HumanReview:
        review = HumanReview(
            tenant_id=tenant_id,
            target_type=target_type,
            target_id=target_id,
            reviewer_id=reviewer_id,
            status="REVIEW_REQUIRED",
        )
        self.session.add(review)
        await self.session.flush()
        await self.session.refresh(review)
        return review

    async def decide(
        self,
        review: HumanReview,
        decision: str,
        *,
        comment: str | None = None,
        reason_code: str | None = None,
        duration_ms: int | None = None,
        event_time: datetime | None = None,
    ) -> HumanReviewEvent:
        if decision not in VALID_DECISIONS:
            raise ValueError(f"invalid review decision: {decision}")
        event_time = event_time or datetime.now(timezone.utc)
        event = HumanReviewEvent(
            review_id=review.id,
            from_status=review.status,
            to_status=decision,
            event_time=event_time,
            comment=comment,
            reason_code=reason_code,
            duration_ms=duration_ms,
        )
        review.status = decision
        review.decision = decision
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def get(
        self, review_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> HumanReview | None:
        result = await self.session.execute(
            select(HumanReview).where(
                HumanReview.id == review_id,
                HumanReview.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_queue(
        self,
        *,
        tenant_id: uuid.UUID,
        statuses: tuple[str, ...] = ("REVIEW_REQUIRED", "UNDER_REVIEW"),
    ) -> list[HumanReview]:
        result = await self.session.execute(
            select(HumanReview)
            .where(
                HumanReview.tenant_id == tenant_id,
                HumanReview.status.in_(statuses),
            )
            .order_by(HumanReview.created_at)
        )
        return list(result.scalars().all())
