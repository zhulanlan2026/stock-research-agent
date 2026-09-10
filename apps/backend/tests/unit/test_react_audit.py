from __future__ import annotations

import uuid
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.agents.react_audit import ReActAuditRecorder
from stock_research.model_gateway.gateway import ModelResponse
from stock_research.stores.models.audit import AuditEvent, ModelUsage


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, value: Any) -> None:
        self.added.append(value)


async def test_react_audit_recorder_persists_model_usage_and_skill_audit() -> None:
    fake_session = _FakeSession()
    session = cast(AsyncSession, fake_session)
    tenant_id = uuid.uuid4()
    task_id = uuid.uuid4()
    user_id = uuid.uuid4()
    recorder = ReActAuditRecorder(
        session,
        tenant_id=tenant_id,
        task_id=str(task_id),
        user_id=user_id,
    )

    await recorder.record_model(
        agent="research",
        task_id=str(task_id),
        alias="research",
        response=ModelResponse(
            content="ok",
            model="deepseek-chat",
            input_tokens=100,
            output_tokens=20,
            latency_ms=50,
        ),
        iteration=1,
    )
    await recorder.record_skill(
        agent="research",
        task_id=str(task_id),
        skill_name="research.context.read",
        allowed=True,
        action_args={"state": {}},
        observation='{"results":{}}',
        iteration=1,
    )

    assert len(fake_session.added) == 2
    model_usage = fake_session.added[0]
    audit_event = fake_session.added[1]
    assert isinstance(model_usage, ModelUsage)
    assert model_usage.tenant_id == tenant_id
    assert model_usage.actual_model == "deepseek-chat"
    assert model_usage.input_tokens == 100
    assert model_usage.estimated_cost > 0
    assert isinstance(audit_event, AuditEvent)
    assert audit_event.action == "EXECUTE"
    assert audit_event.resource_id == "research.context.read"


async def test_react_audit_recorder_skips_invalid_tenant() -> None:
    fake_session = _FakeSession()
    session = cast(AsyncSession, fake_session)
    recorder = ReActAuditRecorder(
        session,
        tenant_id="not-a-uuid",
        task_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
    )

    await recorder.record_model(
        agent="research",
        task_id="task-1",
        alias="research",
        response=ModelResponse(content="ok", model="deepseek-chat"),
        iteration=1,
    )
    await recorder.record_skill(
        agent="research",
        task_id="task-1",
        skill_name="research.context.read",
        allowed=False,
        action_args={},
        observation="denied",
        iteration=1,
    )

    assert fake_session.added == []
