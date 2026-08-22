import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.stores.models.workflow import Task, TaskVersion, WorkflowEvent


class WorkflowEventStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_task(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        symbol: str,
        mode: str,
        as_of: datetime | None,
        modules: list[str],
        question: str | None,
        task_type: str = "research",
        idempotency_key: str | None = None,
    ) -> Task:
        task = Task(
            tenant_id=tenant_id,
            user_id=user_id,
            task_type=task_type,
            status="queued",
            symbol=symbol,
            mode=mode,
            as_of=as_of,
            requested_modules=modules,
            question=question,
            idempotency_key=idempotency_key,
        )
        self.session.add(task)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def get_task(self, task_id: uuid.UUID) -> Task | None:
        return await self.session.get(Task, task_id)

    async def find_task_by_idempotency_key(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID, idempotency_key: str
    ) -> Task | None:
        result = await self.session.execute(
            select(Task).where(
                Task.tenant_id == tenant_id,
                Task.user_id == user_id,
                Task.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def append_event(
        self,
        task_id: uuid.UUID,
        event_type: str,
        stage: str | None = None,
        payload: dict[str, object] | None = None,
        sequence_no: int | None = None,
    ) -> WorkflowEvent:
        if sequence_no is None:
            sequence_no = await self._next_sequence(task_id)
        event = WorkflowEvent(
            task_id=task_id,
            sequence_no=sequence_no,
            event_type=event_type,
            stage=stage,
            payload=payload or {},
        )
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def list_events(self, task_id: uuid.UUID, after_sequence: int = 0) -> list[WorkflowEvent]:
        result = await self.session.execute(
            select(WorkflowEvent)
            .where(
                WorkflowEvent.task_id == task_id,
                WorkflowEvent.sequence_no > after_sequence,
            )
            .order_by(WorkflowEvent.sequence_no)
        )
        return list(result.scalars().all())

    async def create_task_version(
        self, task_id: uuid.UUID, payload: dict[str, object], version_no: int | None = None
    ) -> TaskVersion:
        if version_no is None:
            max_version = (
                await self.session.execute(
                    select(func.max(TaskVersion.version_no)).where(TaskVersion.task_id == task_id)
                )
            ).scalar()
            version_no = (max_version or 0) + 1
        version = TaskVersion(task_id=task_id, version_no=version_no, payload=payload)
        self.session.add(version)
        await self.session.flush()
        return version

    async def _next_sequence(self, task_id: uuid.UUID) -> int:
        max_sequence = (
            await self.session.execute(
                select(func.max(WorkflowEvent.sequence_no)).where(WorkflowEvent.task_id == task_id)
            )
        ).scalar()
        return (max_sequence or 0) + 1
