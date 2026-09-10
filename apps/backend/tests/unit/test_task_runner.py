from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

from stock_research.agents.orchestrator import OrchestrationResult
from stock_research.agents.protocol import AgentResult
from stock_research.market.cycle import CycleAnalysisService
from stock_research.workflow import runner


class _FakeTask:
    def __init__(self) -> None:
        self.id = uuid.uuid4()
        self.tenant_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.symbol = "600519.SH"
        self.mode = "standard"
        self.as_of = datetime(2026, 4, 1, tzinfo=timezone.utc)
        self.requested_modules = ["fundamental", "technical", "market"]
        self.question = "当前技术面和市场风险如何？"


class _FakeSession:
    async def commit(self) -> None:
        return None

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None


class _FakeSessionFactory:
    def __call__(self) -> _FakeSession:
        return _FakeSession()


class _FakeStore:
    def __init__(self, task: _FakeTask) -> None:
        self.task = task
        self.statuses: list[str] = []
        self.events: list[tuple[str, dict[str, Any]]] = []
        self.versions: list[dict[str, Any]] = []

    async def get_task(self, task_id: uuid.UUID) -> _FakeTask | None:
        return self.task if task_id == self.task.id else None

    async def update_task_status(self, task_id: uuid.UUID, status: str) -> _FakeTask:
        self.statuses.append(status)
        return self.task

    async def append_event(
        self,
        task_id: uuid.UUID,
        event_type: str,
        **kwargs: Any,
    ) -> None:
        self.events.append((event_type, kwargs))

    async def create_task_version(
        self,
        task_id: uuid.UUID,
        payload: dict[str, Any],
        version_no: int | None = None,
    ) -> Any:
        self.versions.append(payload)
        return type("_Version", (), {"version_no": 1})()


class _FakeOrchestrator:
    def __init__(
        self,
        registry: Any,
        *,
        prefer_langgraph: bool,
        review_decision: str | None = None,
    ) -> None:
        self.registry = registry
        self.prefer_langgraph = prefer_langgraph
        self.review_decision = review_decision

    async def run(self, context: Any, selected: tuple[str, ...]) -> OrchestrationResult:
        results: dict[str, AgentResult] = {}
        for name in selected:
            data: dict[str, Any] = {}
            if name == "review" and self.review_decision is not None:
                data = {
                    "result": SimpleNamespace(
                        decision=self.review_decision,
                        reason="测试审核",
                    )
                }
            results[name] = AgentResult(
                agent=name,
                status="COMPLETED",
                data=data,
            )
        return OrchestrationResult(results=results, state={}, warnings=())


class _FakeAgent:
    def __init__(self, name: str, dependencies: tuple[str, ...] = ()) -> None:
        self.manifest = type(
            "_Manifest",
            (),
            {"name": name, "dependencies": dependencies},
        )()


class _FakeOutboxEvent:
    def __init__(self, event_type: str) -> None:
        self.event_type = event_type


class _FakeOutboxPublisher:
    def __init__(self, session: Any) -> None:
        self.session = session
        self.published: list[str] = []

    async def publish(self, **kwargs: Any) -> _FakeOutboxEvent | None:
        event_type = str(kwargs["event_type"])
        self.published.append(event_type)
        return _FakeOutboxEvent(event_type)


class _FakeHumanReview:
    id = uuid.uuid4()


class _FakeHumanReviewService:
    def __init__(self, session: Any) -> None:
        self.session = session
        self.created: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> _FakeHumanReview:
        self.created.append(kwargs)
        return _FakeHumanReview()


async def test_run_research_task_marks_running_and_completed(
    monkeypatch: Any,
) -> None:
    task = _FakeTask()
    store = _FakeStore(task)
    monkeypatch.setattr(runner, "session_factory", _FakeSessionFactory())
    monkeypatch.setattr(runner, "WorkflowEventStore", lambda _session: store)
    monkeypatch.setattr(
        runner,
        "build_research_agents",
        _core_agents,
    )
    monkeypatch.setattr(runner, "AgentOrchestrator", _FakeOrchestrator)

    await runner.run_research_task(task.id)

    assert store.statuses == ["running", "completed"]
    assert [event_type for event_type, _payload in store.events] == [
        "task.started",
        "modules.started",
        "agent.completed",
        "agent.completed",
        "agent.completed",
        "modules.completed",
        "task.completed",
    ]
    modules_event = store.events[5][1]["payload"]
    assert modules_event["modules"] == ["fundamental", "technical", "market"]
    assert modules_event["version_no"] == 1
    assert store.versions[0]["results"]["fundamental"]["status"] == "COMPLETED"


async def test_allowed_research_task_enqueues_outbox(monkeypatch: Any) -> None:
    task = _FakeTask()
    task.requested_modules = []
    store = _FakeStore(task)
    outbox = _FakeOutboxPublisher(object())
    monkeypatch.setattr(runner, "session_factory", _FakeSessionFactory())
    monkeypatch.setattr(runner, "WorkflowEventStore", lambda _session: store)
    monkeypatch.setattr(runner, "build_research_agents", _all_agents)
    monkeypatch.setattr(
        runner,
        "AgentOrchestrator",
        lambda registry, *, prefer_langgraph: _FakeOrchestrator(
            registry,
            prefer_langgraph=prefer_langgraph,
            review_decision="APPROVED",
        ),
    )
    monkeypatch.setattr(runner, "OutboxPublisher", lambda _session: outbox)

    await runner.run_research_task(task.id)

    assert outbox.published == ["research.approved"]
    assert store.statuses[-1] == "completed"
    assert "outbox.enqueued" in [event_type for event_type, _ in store.events]


async def test_review_required_task_creates_human_review(monkeypatch: Any) -> None:
    task = _FakeTask()
    task.requested_modules = []
    store = _FakeStore(task)
    human_review = _FakeHumanReviewService(object())
    monkeypatch.setattr(runner, "session_factory", _FakeSessionFactory())
    monkeypatch.setattr(runner, "WorkflowEventStore", lambda _session: store)
    monkeypatch.setattr(runner, "build_research_agents", _all_agents)
    monkeypatch.setattr(
        runner,
        "AgentOrchestrator",
        lambda registry, *, prefer_langgraph: _FakeOrchestrator(
            registry,
            prefer_langgraph=prefer_langgraph,
            review_decision="NEEDS_REVISION",
        ),
    )
    monkeypatch.setattr(runner, "HumanReviewService", lambda _session: human_review)

    await runner.run_research_task(task.id)

    assert human_review.created[0]["target_type"] == "research_task"
    assert store.statuses[-1] == "review_required"
    assert "human_review.created" in [event_type for event_type, _ in store.events]


def _all_agents(
    _factory: Any,
    _model_gateway: Any | None = None,
    *,
    model_alias: str = "research",
    react_observer: Any | None = None,
    cycle_service: Any | None = None,
) -> list[_FakeAgent]:
    return [
        _FakeAgent("fundamental"),
        _FakeAgent("technical"),
        _FakeAgent("market"),
        _FakeAgent("news"),
        _FakeAgent("supply_chain"),
        _FakeAgent(
            "risk",
            dependencies=("fundamental", "technical", "market"),
        ),
        _FakeAgent(
            "research",
            dependencies=(
                "fundamental",
                "technical",
                "market",
                "supply_chain",
                "news",
                "risk",
            ),
        ),
        _FakeAgent("report", dependencies=("research",)),
        _FakeAgent("review", dependencies=("report",)),
    ]


def _core_agents(
    _factory: Any,
    _model_gateway: Any | None = None,
    *,
    model_alias: str = "research",
    react_observer: Any | None = None,
    cycle_service: Any | None = None,
) -> list[_FakeAgent]:
    return [
        _FakeAgent("fundamental"),
        _FakeAgent("technical"),
        _FakeAgent("market"),
        _FakeAgent(
            "risk",
            dependencies=("fundamental", "technical", "market"),
        ),
    ]


def test_build_cycle_service_disables_lstm_by_default() -> None:
    settings = SimpleNamespace(technical_lstm_enabled=False)

    service = runner._build_cycle_service(settings)

    assert isinstance(service, CycleAnalysisService)
    assert service._lstm_predictor is None


def test_build_cycle_service_enables_lstm_predictor() -> None:
    settings = SimpleNamespace(
        technical_lstm_enabled=True,
        technical_lstm_seed=1,
        technical_lstm_hidden_size=16,
        technical_lstm_epochs=10,
        technical_lstm_window=12,
    )

    service = runner._build_cycle_service(settings)

    assert isinstance(service, CycleAnalysisService)
    assert service._lstm_predictor is not None
