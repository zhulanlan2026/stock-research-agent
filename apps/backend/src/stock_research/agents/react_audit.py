from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.model_gateway.deepseek import estimate_cost
from stock_research.model_gateway.gateway import ModelResponse
from stock_research.stores.models.audit import AuditEvent, ModelUsage


class ReActAuditRecorder:
    """把 ReAct 模型调用和 Skill 调用写入审计表。

    不自行 commit；由外层研究任务事务统一提交，保证 workflow 与审计一致。
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        tenant_id: str | uuid.UUID | None,
        task_id: str | uuid.UUID | None,
        user_id: str | uuid.UUID | None,
    ) -> None:
        self._session = session
        self._tenant_id = _as_uuid(tenant_id)
        self._task_id = _as_uuid(task_id)
        self._user_id = _as_uuid(user_id)

    async def record_model(
        self,
        *,
        agent: str,
        task_id: str | None,
        alias: str,
        response: ModelResponse,
        iteration: int,
    ) -> None:
        if self._tenant_id is None:
            return
        self._session.add(
            ModelUsage(
                tenant_id=self._tenant_id,
                task_id=self._task_id,
                alias=alias,
                actual_model=response.model,
                prompt_version="react:1.0.0",
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                latency_ms=response.latency_ms,
                estimated_cost=estimate_cost(
                    response.model,
                    response.input_tokens,
                    response.output_tokens,
                ),
                retry_count=0,
                cache_hit=False,
                request_id=_request_id(agent, task_id, iteration),
            )
        )

    async def record_skill(
        self,
        *,
        agent: str,
        task_id: str | None,
        skill_name: str,
        allowed: bool,
        action_args: dict[str, Any],
        observation: str,
        iteration: int,
    ) -> None:
        if self._tenant_id is None:
            return
        self._session.add(
            AuditEvent(
                tenant_id=self._tenant_id,
                actor_user_id=self._user_id,
                event_type="react.skill",
                resource_type="skill",
                resource_id=skill_name,
                action="EXECUTE" if allowed else "DENY",
                request_id=_request_id(agent, task_id, iteration),
                ip=None,
                metadata_={
                    "agent": agent,
                    "task_id": task_id,
                    "allowed": allowed,
                    "action_args": _jsonable(action_args),
                    "observation_size": len(observation),
                },
            )
        )


def _as_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _request_id(agent: str, task_id: str | None, iteration: int) -> str:
    return f"{agent}:{task_id or 'unknown'}:{iteration}"


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return str(value)
