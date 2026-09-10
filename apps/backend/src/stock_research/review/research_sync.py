from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.outbox.publisher import OutboxPublisher
from stock_research.stores.models.review import HumanReview
from stock_research.workflow.store import WorkflowEventStore


async def apply_research_review_decision(
    session: AsyncSession,
    review: HumanReview,
    decision: str,
) -> None:
    if review.target_type != "research_task":
        return

    task_id = uuid.UUID(review.target_id)
    store = WorkflowEventStore(session)
    await store.append_event(
        task_id,
        "human_review.decided",
        stage="review",
        payload={"decision": decision, "review_id": str(review.id)},
    )

    if decision == "APPROVED":
        outbox_event = await OutboxPublisher(session).publish(
            aggregate_type="research_task",
            aggregate_id=str(task_id),
            event_type="research.approved",
            payload={
                "task_id": str(task_id),
                "review_id": str(review.id),
                "decision": decision,
            },
        )
        if outbox_event is not None:
            await store.append_event(
                task_id,
                "outbox.enqueued",
                stage="outbox",
                payload={"event_type": outbox_event.event_type},
            )
        await store.update_task_status(task_id, "completed")
    elif decision == "REJECTED":
        await store.update_task_status(task_id, "rejected")
    else:
        await store.update_task_status(task_id, "needs_revision")
