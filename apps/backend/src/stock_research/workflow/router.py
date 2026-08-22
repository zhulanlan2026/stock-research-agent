import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.auth.dependencies import get_current_user
from stock_research.stores.models.iam import User
from stock_research.stores.session import get_session
from stock_research.workflow.schemas import TaskCreateRequest, TaskResponse
from stock_research.workflow.sse import format_sse, parse_last_event_id
from stock_research.workflow.store import WorkflowEventStore

router = APIRouter(prefix="/research", tags=["workflow"])


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_task(
    body: TaskCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    store = WorkflowEventStore(session)
    idempotency_key = request.headers.get("Idempotency-Key")
    if idempotency_key is not None:
        existing = await store.find_task_by_idempotency_key(
            current_user.tenant_id, current_user.id, idempotency_key
        )
        if existing is not None:
            return TaskResponse.model_validate(existing)

    task = await store.create_task(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        symbol=body.symbol,
        mode=body.mode,
        as_of=body.as_of,
        modules=body.modules,
        question=body.question,
        idempotency_key=idempotency_key,
    )
    await session.commit()
    return TaskResponse.model_validate(task)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    task = await WorkflowEventStore(session).get_task(task_id)
    if task is None or task.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_NOT_FOUND", "message": "任务不存在"},
        )
    return TaskResponse.model_validate(task)


@router.get("/tasks/{task_id}/events")
async def task_events(
    task_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    store = WorkflowEventStore(session)
    task = await store.get_task(task_id)
    if task is None or task.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_NOT_FOUND", "message": "任务不存在"},
        )

    after_sequence = parse_last_event_id(request.headers.get("Last-Event-ID"))
    events = await store.list_events(task_id, after_sequence)

    async def event_stream() -> AsyncGenerator[str, None]:
        for event in events:
            yield format_sse(event)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
