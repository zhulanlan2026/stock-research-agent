import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.auth.dependencies import get_current_user
from stock_research.fundamental.report import ReportService
from stock_research.fundamental.research import DEFAULT_SCENARIOS, StandardResearchService
from stock_research.stores.models.iam import User
from stock_research.stores.session import get_session
from stock_research.workflow.runner import run_research_task
from stock_research.workflow.schemas import (
    ReportRequest,
    ReportResponse,
    ReportSectionResponse,
    TaskCreateRequest,
    TaskResponse,
    TaskVersionResponse,
)
from stock_research.workflow.sse import format_sse, parse_last_event_id
from stock_research.workflow.store import WorkflowEventStore

router = APIRouter(prefix="/research", tags=["workflow"])


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_task(
    body: TaskCreateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
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
    background_tasks.add_task(run_research_task, task.id)
    return TaskResponse.model_validate(task)


@router.post("/reports", response_model=ReportResponse, status_code=status.HTTP_200_OK)
async def generate_report(
    body: ReportRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ReportResponse:
    as_of = body.as_of or datetime.now(timezone.utc)
    result = await StandardResearchService(session).run(
        symbol=body.symbol,
        as_of=as_of,
        scenarios=list(DEFAULT_SCENARIOS),
        peers=[],
    )
    report = ReportService().render(result)
    return ReportResponse(
        symbol=report.symbol,
        as_of=report.as_of,
        module_version=report.module_version,
        summary=report.summary,
        sections=[
            ReportSectionResponse(title=section.title, data=section.data)
            for section in report.sections
        ],
    )


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


@router.get("/tasks/{task_id}/versions", response_model=list[TaskVersionResponse])
async def task_versions(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[TaskVersionResponse]:
    store = WorkflowEventStore(session)
    task = await store.get_task(task_id)
    if task is None or task.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_NOT_FOUND", "message": "任务不存在"},
        )
    versions = await store.list_task_versions(task_id)
    return [TaskVersionResponse.model_validate(version) for version in versions]


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
    async def event_stream() -> AsyncGenerator[str, None]:
        current_after = after_sequence
        terminal_statuses = {"completed", "failed", "rejected", "review_required"}
        while True:
            events = await store.list_events(task_id, current_after)
            for event in events:
                yield format_sse(event)
                current_after = event.sequence_no

            await session.refresh(task)
            if task.status in terminal_statuses:
                break
            if await request.is_disconnected():
                break
            await asyncio.sleep(1)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
