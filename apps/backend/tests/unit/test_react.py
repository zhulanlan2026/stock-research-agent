from __future__ import annotations

from typing import Any

import pytest

from stock_research.agents.react import (
    ReActBudgetExceededError,
    ReActLimits,
    ReActLoop,
    ReActMaxIterationsError,
)
from stock_research.agents.react_skills import ResearchContextSkill
from stock_research.model_gateway.gateway import (
    ModelGateway,
    ModelRequest,
    ModelResponse,
)
from stock_research.skills.gateway import SkillGateway


class _FakeModelClient:
    def __init__(self, responses: list[ModelResponse]) -> None:
        self._responses = responses
        self.requests: list[ModelRequest] = []

    async def complete(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        return self._responses.pop(0)


def _gateway() -> SkillGateway:
    gateway = SkillGateway()
    gateway.register_skill(
        ResearchContextSkill.manifest,
        ResearchContextSkill().execute,
    )
    return gateway


def _response(content: str) -> ModelResponse:
    return ModelResponse(content=content, model="fake-model")


class _RecordingObserver:
    def __init__(self) -> None:
        self.models: list[dict[str, Any]] = []
        self.skills: list[dict[str, Any]] = []

    async def record_model(self, **kwargs: Any) -> None:
        self.models.append(kwargs)

    async def record_skill(self, **kwargs: Any) -> None:
        self.skills.append(kwargs)


async def test_react_loop_executes_allowed_skill_then_final_answer() -> None:
    client = _FakeModelClient(
        [
            _response(
                '{"thought":"先读上下文","action":{"skill":"research.context.read","args":{"state":{"results":{"technical":{"status":"COMPLETED"}}}}}}'
            ),
            _response(
                '{"thought":"已有足够信息","final_answer":"600519.SH 技术面已完成。"}'
            ),
        ]
    )
    gateway = _gateway()

    result = await ReActLoop(ModelGateway(client), gateway).run(
        system_prompt="system",
        user_prompt="user",
        agent="research",
        task_id="task-1",
        scopes=frozenset({"research.standard.execute"}),
        allowed_skills=frozenset({"research.context.read"}),
        model="research",
    )

    assert result.final_answer == "600519.SH 技术面已完成。"
    assert result.model_calls == 2
    assert result.steps[0].action == "research.context.read"
    assert "COMPLETED" in (result.steps[0].observation or "")


async def test_react_loop_denies_skill_not_in_allowlist() -> None:
    client = _FakeModelClient(
        [
            _response(
                '{"thought":"尝试越权","action":{"skill":"dangerous.execute","args":{}}}'
            ),
            _response('{"thought":"停止","final_answer":"done"}'),
        ]
    )

    result = await ReActLoop(ModelGateway(client), _gateway()).run(
        system_prompt="system",
        user_prompt="user",
        agent="research",
        task_id="task-1",
        scopes=frozenset(),
        allowed_skills=frozenset(),
        model="research",
    )

    assert result.final_answer == "done"
    assert result.steps[0].observation == (
        "SKILL_DENIED: 不允许调用 skill=dangerous.execute"
    )


async def test_react_loop_accepts_direct_final_answer() -> None:
    client = _FakeModelClient(
        [_response('{"thought":"无需动作","final_answer":"最终结论"}')]
    )

    result = await ReActLoop(ModelGateway(client), _gateway()).run(
        system_prompt="system",
        user_prompt="user",
        agent="research",
        task_id="task-1",
        scopes=frozenset(),
        allowed_skills=frozenset(),
        model="research",
    )

    assert result.final_answer == "最终结论"
    assert len(result.steps) == 1
    assert result.steps[0].action is None


async def test_react_loop_raises_after_max_iterations() -> None:
    client = _FakeModelClient(
        [
            _response("not-json"),
            _response("not-json"),
        ]
    )

    with pytest.raises(ReActMaxIterationsError):
        await ReActLoop(
            ModelGateway(client),
            _gateway(),
            limits=ReActLimits(max_iterations=2),
        ).run(
            system_prompt="system",
            user_prompt="user",
            agent="research",
            task_id="task-1",
            scopes=frozenset(),
            allowed_skills=frozenset(),
            model="research",
        )


async def test_react_loop_records_model_and_skill_observer_events() -> None:
    client = _FakeModelClient(
        [
            _response(
                '{"thought":"先读上下文","action":{"skill":"research.context.read","args":{"state":{}}}}'
            ),
            _response('{"thought":"完成","final_answer":"结论"}'),
        ]
    )
    observer = _RecordingObserver()

    result = await ReActLoop(
        ModelGateway(client),
        _gateway(),
        observer=observer,
    ).run(
        system_prompt="system",
        user_prompt="user",
        agent="research",
        task_id="task-1",
        scopes=frozenset({"research.standard.execute"}),
        allowed_skills=frozenset({"research.context.read"}),
        model="research",
    )

    assert result.final_answer == "结论"
    assert len(observer.models) == 2
    assert observer.models[0]["alias"] == "research"
    assert len(observer.skills) == 1
    assert observer.skills[0]["skill_name"] == "research.context.read"
    assert observer.skills[0]["allowed"] is True


async def test_react_loop_enforces_token_budget() -> None:
    client = _FakeModelClient(
        [
            ModelResponse(
                content='{"final_answer":"不应到达"}',
                model="fake-model",
                input_tokens=30,
            )
        ]
    )

    with pytest.raises(ReActBudgetExceededError):
        await ReActLoop(
            ModelGateway(client),
            _gateway(),
            limits=ReActLimits(max_total_input_tokens=10),
        ).run(
            system_prompt="system",
            user_prompt="user",
            agent="research",
            task_id="task-1",
            scopes=frozenset(),
            allowed_skills=frozenset(),
            model="research",
        )
