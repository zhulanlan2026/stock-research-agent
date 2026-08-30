from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.stores.models.workflow import CheckpointRef


class CheckpointStore:
    """持久化 LangGraph 阶段 Checkpoint。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(
        self,
        *,
        task_id: uuid.UUID,
        checkpoint_id: str,
        node_id: str | None,
        state: dict[str, object],
    ) -> CheckpointRef:
        checkpoint = CheckpointRef(
            task_id=task_id,
            checkpoint_id=checkpoint_id,
            node_id=node_id,
            state=state,
        )
        self.session.add(checkpoint)
        await self.session.flush()
        await self.session.refresh(checkpoint)
        return checkpoint

    async def get(self, checkpoint_id: str) -> CheckpointRef | None:
        result = await self.session.execute(
            select(CheckpointRef).where(CheckpointRef.checkpoint_id == checkpoint_id)
        )
        return result.scalar_one_or_none()

    async def list_for_task(self, task_id: uuid.UUID) -> list[CheckpointRef]:
        result = await self.session.execute(
            select(CheckpointRef)
            .where(CheckpointRef.task_id == task_id)
            .order_by(CheckpointRef.created_at)
        )
        return list(result.scalars().all())
