from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from stock_research.model_gateway.gateway import (
    ModelGateway,
    ModelMessage,
    ModelRequest,
    ModelResponse,
)
from stock_research.skills.gateway import SkillCallContext, SkillDeniedError, SkillGateway


@dataclass(frozen=True)
class ReActStep:
    step: int
    thought: str | None
    action: str | None
    action_args: dict[str, Any]
    observation: str | None


@dataclass(frozen=True)
class ReActResult:
    final_answer: str
    steps: tuple[ReActStep, ...]
    model_calls: int


@dataclass(frozen=True)
class ReActLimits:
    max_iterations: int = 5
    max_total_input_tokens: int = 20_000
    max_total_output_tokens: int = 8_000


class ReActObserver(Protocol):
    async def record_model(
        self,
        *,
        agent: str,
        task_id: str | None,
        alias: str,
        response: ModelResponse,
        iteration: int,
    ) -> None:
        ...

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
        ...


class ReActValidationError(RuntimeError):
    pass


class ReActMaxIterationsError(RuntimeError):
    pass


class ReActBudgetExceededError(RuntimeError):
    pass


class ReActLoop:
    """受控 ReAct 循环。

    模型输出必须使用 Thought/Action/Observation 或 Final Answer JSON。
    所有 Action 都经 SkillGateway 执行，且只允许显式声明的 skills。
    """

    def __init__(
        self,
        model_gateway: ModelGateway,
        skill_gateway: SkillGateway,
        *,
        limits: ReActLimits | None = None,
        observer: ReActObserver | None = None,
    ) -> None:
        self._model_gateway = model_gateway
        self._skill_gateway = skill_gateway
        self._limits = limits or ReActLimits()
        self._observer = observer

    async def run(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        agent: str,
        task_id: str | None,
        scopes: frozenset[str],
        allowed_skills: frozenset[str],
        model: str,
        tenant_id: str | None = None,
        user_id: str | None = None,
    ) -> ReActResult:
        messages = [
            ModelMessage(role="system", content=system_prompt),
            ModelMessage(role="user", content=user_prompt),
        ]
        steps: list[ReActStep] = []
        total_input_tokens = 0
        total_output_tokens = 0

        for iteration in range(1, self._limits.max_iterations + 1):
            response = await self._model_gateway.complete(
                ModelRequest(
                    model=model,
                    messages=list(messages),
                    temperature=0.1,
                    max_tokens=1024,
                ),
                tenant_id=tenant_id,
                user_id=user_id,
            )
            total_input_tokens += response.input_tokens
            total_output_tokens += response.output_tokens
            if self._observer is not None:
                await self._observer.record_model(
                    agent=agent,
                    task_id=task_id,
                    alias=model,
                    response=response,
                    iteration=iteration,
                )
            if (
                total_input_tokens > self._limits.max_total_input_tokens
                or total_output_tokens > self._limits.max_total_output_tokens
            ):
                raise ReActBudgetExceededError(
                    "ReAct token budget exceeded: "
                    f"input={total_input_tokens}/{self._limits.max_total_input_tokens}, "
                    f"output={total_output_tokens}/{self._limits.max_total_output_tokens}"
                )
            parsed = _parse_json_object(response.content)
            if parsed is None:
                observation = "输出不是合法 JSON；请只返回 action 或 final_answer。"
                messages.append(ModelMessage(role="user", content=observation))
                steps.append(
                    ReActStep(
                        step=iteration,
                        thought=None,
                        action=None,
                        action_args={},
                        observation=observation,
                    )
                )
                continue

            thought = _optional_text(parsed.get("thought"))
            final_answer = parsed.get("final_answer")
            if final_answer is not None:
                answer = str(final_answer).strip()
                if not answer:
                    raise ReActValidationError("final_answer must not be empty")
                steps.append(
                    ReActStep(
                        step=iteration,
                        thought=thought,
                        action=None,
                        action_args={},
                        observation=None,
                    )
                )
                return ReActResult(
                    final_answer=answer,
                    steps=tuple(steps),
                    model_calls=iteration,
                )

            action = parsed.get("action")
            if not isinstance(action, dict):
                observation = "action 必须是对象，例如 {\"skill\": \"...\", \"args\": {}}。"
                messages.append(ModelMessage(role="user", content=observation))
                steps.append(
                    ReActStep(
                        step=iteration,
                        thought=thought,
                        action=None,
                        action_args={},
                        observation=observation,
                    )
                )
                continue

            skill_name = _optional_text(action.get("skill"))
            action_args = action.get("args") or {}
            allowed = (
                skill_name is not None
                and isinstance(action_args, dict)
                and skill_name in allowed_skills
            )
            if skill_name is None:
                observation = "action.skill 不能为空。"
            elif not isinstance(action_args, dict):
                observation = "action.args 必须是对象。"
            elif skill_name not in allowed_skills:
                observation = f"SKILL_DENIED: 不允许调用 skill={skill_name}"
            else:
                try:
                    skill_result = await self._skill_gateway.execute(
                        skill_name,
                        SkillCallContext(
                            scopes=scopes,
                            agent=agent,
                            task_id=task_id,
                        ),
                        **action_args,
                    )
                    observation = _json_text(skill_result)
                except SkillDeniedError as exc:
                    observation = f"SKILL_DENIED: {exc}"
                except Exception as exc:
                    observation = f"SKILL_ERROR: {type(exc).__name__}: {exc}"

            if self._observer is not None:
                await self._observer.record_skill(
                    agent=agent,
                    task_id=task_id,
                    skill_name=skill_name or "unknown",
                    allowed=allowed,
                    action_args=dict(action_args),
                    observation=observation,
                    iteration=iteration,
                )

            messages.append(ModelMessage(role="user", content=observation))
            steps.append(
                ReActStep(
                    step=iteration,
                    thought=thought,
                    action=skill_name,
                    action_args=dict(action_args),
                    observation=observation,
                )
            )

        raise ReActMaxIterationsError(
            f"ReAct loop exceeded max iterations: {self._limits.max_iterations}"
        )


def _parse_json_object(content: str) -> dict[str, Any] | None:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _json_text(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        default=str,
        separators=(",", ":"),
    )
