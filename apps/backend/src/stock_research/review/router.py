import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.auth.dependencies import get_current_user
from stock_research.review.human_review import HumanReviewService
from stock_research.review.research_sync import apply_research_review_decision
from stock_research.review.schemas import ReviewDecisionRequest, ReviewResponse
from stock_research.stores.models.iam import User
from stock_research.stores.session import get_session

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/queue", response_model=list[ReviewResponse])
async def list_review_queue(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ReviewResponse]:
    reviews = await HumanReviewService(session).list_queue(
        tenant_id=current_user.tenant_id
    )
    return [ReviewResponse.model_validate(review) for review in reviews]


@router.post("/{review_id}/decision", response_model=ReviewResponse)
async def decide_review(
    review_id: uuid.UUID,
    body: ReviewDecisionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ReviewResponse:
    service = HumanReviewService(session)
    review = await service.get(review_id, tenant_id=current_user.tenant_id)
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "REVIEW_NOT_FOUND", "message": "审核项不存在"},
        )
    await service.decide(
        review,
        body.decision,
        comment=body.comment,
        reason_code=body.reason_code,
    )
    await apply_research_review_decision(session, review, body.decision)
    await session.commit()
    return ReviewResponse.model_validate(review)
