from __future__ import annotations

import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, cast

import structlog

from stock_research.agents.engine_agents import build_research_agents
from stock_research.agents.orchestrator import AgentOrchestrator, OrchestrationResult
from stock_research.agents.protocol import AgentContext
from stock_research.agents.react_audit import ReActAuditRecorder
from stock_research.agents.registry import AgentRegistry
from stock_research.core.config import get_settings
from stock_research.market.cycle import CycleAnalysisService
from stock_research.market.torch_lstm import TorchLstmCyclePredictor
from stock_research.model_gateway.deepseek import DeepSeekClient
from stock_research.model_gateway.gateway import ModelGateway
from stock_research.outbox.publisher import OutboxPublisher
from stock_research.review.human_review import HumanReviewService
from stock_research.stores.session import session_factory
from stock_research.workflow.store import WorkflowEventStore

logger = structlog.get_logger(__name__)

RESEARCH_MODULES = (
    "fundamental",
    "technical",
    "market",
    "supply_chain",
    "news",
    "risk",
    "research",
    "report",
    "review",
)


async def run_research_task(task_id: uuid.UUID) -> None:
    try:
        await _run_research_task(task_id)
    except Exception:
        logger.exception("research task runner failed", task_id=str(task_id))


async def _run_research_task(task_id: uuid.UUID) -> None:
    settings = get_settings()
    deepseek_client: DeepSeekClient | None = None
    model_gateway: ModelGateway | None = None
    if settings.llm_api_key:
        deepseek_client = DeepSeekClient(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
        )
        model_gateway = ModelGateway(deepseek_client)
    cycle_service = _build_cycle_service(settings)

    try:
        async with session_factory() as session:
            store = WorkflowEventStore(session)
            task = await store.get_task(task_id)
            if task is None:
                return

            await store.update_task_status(task_id, "running")
            await store.append_event(
                task_id,
                "task.started",
                stage="research",
                payload={"message": "研究任务开始", "task_id": str(task_id)},
            )
            await session.commit()

            try:
                react_observer = None
                if model_gateway is not None:
                    react_observer = ReActAuditRecorder(
                        session,
                        tenant_id=task.tenant_id,
                        task_id=str(task.id),
                        user_id=task.user_id,
                    )

                requested = set(task.requested_modules or [])
                selected = tuple(
                    module for module in RESEARCH_MODULES if module in requested
                ) if requested else RESEARCH_MODULES
                unsupported = requested - set(RESEARCH_MODULES)

                registry = AgentRegistry(
                    build_research_agents(
                        session_factory,
                        model_gateway,
                        model_alias=settings.llm_model,
                        react_observer=react_observer,
                        cycle_service=cycle_service,
                    )
                )
                orchestrator = AgentOrchestrator(registry, prefer_langgraph=True)
                plan = registry.execution_plan(selected)
                executed = plan.flat

                await store.append_event(
                    task_id,
                    "modules.started",
                    stage="research",
                    payload={"modules": list(executed)},
                )

                context = AgentContext(
                    task_id=str(task.id),
                    symbol=task.symbol,
                    mode=task.mode,
                    as_of=task.as_of or datetime.now(timezone.utc),
                    purpose=task.question,
                    tenant_id=str(task.tenant_id),
                    user_id=str(task.user_id),
                    scopes=frozenset({"research.standard.execute"}),
                    state={
                        "technical_period": "1d",
                        "technical_cycle_horizon": settings.technical_cycle_horizon,
                        "market_limit": 20,
                        "news_limit": 20,
                        "risk_period": "1d",
                        "risk_limit": 252,
                    },
                )
                result = await orchestrator.run(context, selected)

                for name, agent_result in result.results.items():
                    await store.append_event(
                        task_id,
                        "agent.completed",
                        stage=name,
                        payload={
                            "agent": name,
                            "status": agent_result.status,
                            "module_versions": dict(agent_result.module_versions),
                        },
                    )

                review_decision, review_reason, policy_decision = _review_outcome(result)
                if review_decision is not None:
                    await store.append_event(
                        task_id,
                        "review.completed",
                        stage="review",
                        payload={
                            "decision": review_decision,
                            "reason": review_reason,
                        },
                    )
                    await store.append_event(
                        task_id,
                        "policy.decision",
                        stage="policy",
                        payload={"decision": policy_decision},
                    )

                version = await store.create_task_version(
                    task_id,
                    _build_task_version_payload(
                        task=task,
                        result=result,
                        selected=executed,
                        unsupported=unsupported,
                        review_decision=review_decision,
                        review_reason=review_reason,
                        policy_decision=policy_decision,
                    ),
                )
                await store.append_event(
                    task_id,
                    "modules.completed",
                    stage="research",
                    payload={
                        "modules": list(executed),
                        "statuses": {
                            name: agent_result.status
                            for name, agent_result in result.results.items()
                        },
                        "warnings": list(result.warnings),
                        "unsupported_modules": sorted(unsupported),
                        "version_no": version.version_no,
                    },
                )
                if policy_decision == "REVIEW":
                    human_review = await HumanReviewService(session).create(
                        tenant_id=task.tenant_id,
                        target_type="research_task",
                        target_id=str(task.id),
                        reviewer_id=task.user_id,
                    )
                    await store.append_event(
                        task_id,
                        "human_review.created",
                        stage="review",
                        payload={"review_id": str(human_review.id)},
                    )
                    await store.append_event(
                        task_id,
                        "task.review_required",
                        stage="review",
                        payload={
                            "message": "研究任务需要人工审核",
                            "version_no": version.version_no,
                        },
                    )
                    await store.update_task_status(task_id, "review_required")
                elif policy_decision == "DENY":
                    await store.append_event(
                        task_id,
                        "task.rejected",
                        stage="policy",
                        payload={"message": "研究任务被策略拒绝", "version_no": version.version_no},
                    )
                    await store.update_task_status(task_id, "rejected")
                elif policy_decision is None:
                    await store.append_event(
                        task_id,
                        "task.completed",
                        stage="research",
                        payload={"message": "研究任务完成", "version_no": version.version_no},
                    )
                    await store.update_task_status(task_id, "completed")
                else:
                    outbox_event = await OutboxPublisher(session).publish(
                        aggregate_type="research_task",
                        aggregate_id=str(task.id),
                        event_type="research.approved",
                        payload={
                            "task_id": str(task.id),
                            "symbol": task.symbol,
                            "version_no": version.version_no,
                        },
                    )
                    if outbox_event is not None:
                        await store.append_event(
                            task_id,
                            "outbox.enqueued",
                            stage="outbox",
                            payload={"event_type": outbox_event.event_type},
                        )
                    await store.append_event(
                        task_id,
                        "task.completed",
                        stage="research",
                        payload={"message": "研究任务完成", "version_no": version.version_no},
                    )
                    await store.update_task_status(task_id, "completed")
                await session.commit()
            except Exception as exc:
                await store.append_event(
                    task_id,
                    "task.failed",
                    stage="research",
                    payload={"message": str(exc), "error_type": type(exc).__name__},
                )
                await store.update_task_status(task_id, "failed")
                await session.commit()
    finally:
        if deepseek_client is not None:
            await deepseek_client.aclose()


def _build_cycle_service(settings: Any) -> CycleAnalysisService:
    if not settings.technical_lstm_enabled:
        return CycleAnalysisService()

    predictor = TorchLstmCyclePredictor(
        seed=settings.technical_lstm_seed,
        hidden_size=settings.technical_lstm_hidden_size,
        epochs=settings.technical_lstm_epochs,
        window=settings.technical_lstm_window,
    )
    return CycleAnalysisService(lstm_predictor=predictor)


def _build_task_version_payload(
    *,
    task: Any,
    result: OrchestrationResult,
    selected: tuple[str, ...],
    unsupported: set[str],
    review_decision: str | None,
    review_reason: str | None,
    policy_decision: str | None,
) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "symbol": task.symbol,
        "mode": task.mode,
        "as_of": task.as_of.isoformat() if task.as_of is not None else None,
        "modules": list(selected),
        "unsupported_modules": sorted(unsupported),
        "warnings": list(result.warnings),
        "review_decision": review_decision,
        "review_reason": review_reason,
        "policy_decision": policy_decision,
        "results": {
            name: _agent_result_summary(agent_result)
            for name, agent_result in result.results.items()
        },
    }


def _review_outcome(
    result: OrchestrationResult,
) -> tuple[str | None, str | None, str | None]:
    review_result = result.results.get("review")
    if review_result is None or review_result.status != "COMPLETED":
        return None, None, None
    review = review_result.data.get("result")
    if review is None:
        return None, None, None
    decision = str(getattr(review, "decision", ""))
    reason = str(getattr(review, "reason", ""))
    policy_decision = _policy_decision(decision)
    return decision, reason, policy_decision


def _policy_decision(decision: str) -> str:
    if decision == "APPROVED":
        return "ALLOW"
    if decision == "NEEDS_REVISION":
        return "REVIEW"
    return "DENY"


def _agent_result_summary(agent_result: Any) -> dict[str, object]:
    return {
        "agent": agent_result.agent,
        "status": agent_result.status,
        "module_versions": dict(agent_result.module_versions),
        "latency_ms": agent_result.latency_ms,
        "data": _jsonable(agent_result.data),
    }


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return {
            key: _jsonable(item)
            for key, item in asdict(cast(Any, value)).items()
        }
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return str(value)
