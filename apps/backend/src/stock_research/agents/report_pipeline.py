from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any

from stock_research.agents.protocol import (
    AgentContext,
    AgentManifest,
    AgentResult,
)
from stock_research.agents.react import ReActLimits, ReActLoop, ReActObserver
from stock_research.model_gateway.gateway import ModelGateway
from stock_research.skills.gateway import SkillGateway

REPORT_VERSION = "report:1.1.0"
REVIEW_VERSION = "review:1.1.0"


@dataclass(frozen=True)
class StructuredReportSection:
    title: str
    data: dict[str, Any]


@dataclass(frozen=True)
class StructuredReportResult:
    symbol: str
    as_of: object
    module_version: str
    summary: str
    sections: tuple[StructuredReportSection, ...]
    narrative: str | None = None
    react_trace: dict[str, Any] | None = None


@dataclass(frozen=True)
class StructuredReviewResult:
    decision: str
    reason: str
    report_summary: str
    review_note: str | None = None
    react_trace: dict[str, Any] | None = None


class StructuredReportAgent:
    """将 ResearchSummaryResult 渲染成结构化投研报告。

    默认确定性渲染；注入模型后额外生成报告叙述，模型失败时回退。
    """

    _manifest = AgentManifest(
        name="report",
        version=REPORT_VERSION,
        description="将研究快照渲染为结构化报告并可选生成叙述",
        execution_type="model_driven",
        required_scopes=frozenset({"report.read"}),
        allowed_skills=frozenset(),
        external_model_allowed=True,
        side_effect="NONE",
        dependencies=("research",),
    )

    def __init__(
        self,
        *,
        model_gateway: ModelGateway | None = None,
        skill_gateway: SkillGateway | None = None,
        observer: ReActObserver | None = None,
        model_alias: str = "research",
    ) -> None:
        self._model_gateway = model_gateway
        self._skill_gateway = skill_gateway
        self._observer = observer
        self._model_alias = model_alias

    @property
    def manifest(self) -> AgentManifest:
        return self._manifest

    async def run(self, context: AgentContext) -> AgentResult:
        research = _result(context, "research")
        if research is None:
            return AgentResult(
                agent=self.manifest.name,
                status="FAILED",
                data={"error": "research result is missing"},
            )

        report = StructuredReportResult(
            symbol=context.symbol,
            as_of=context.as_of,
            module_version=REPORT_VERSION,
            summary=research.summary_text,
            sections=(
                StructuredReportSection(
                    "概览",
                    {
                        "symbol": context.symbol,
                        "coverage": research.coverage,
                        "risk_level": _nested(
                            research.module_summaries,
                            "risk",
                            "risk_level",
                        ),
                    },
                ),
                StructuredReportSection(
                    "财务",
                    research.module_summaries.get("fundamental", {}),
                ),
                StructuredReportSection(
                    "技术",
                    research.module_summaries.get("technical", {}),
                ),
                StructuredReportSection(
                    "周期分析",
                    {
                        "fft_periods": _nested(
                            research.module_summaries,
                            "technical",
                            "fft_periods",
                        )
                        or [],
                        "wavelet_energy": _nested(
                            research.module_summaries,
                            "technical",
                            "wavelet_energy",
                        )
                        or [],
                        "lstm_available": _nested(
                            research.module_summaries,
                            "technical",
                            "lstm_available",
                        ),
                        "lstm_latency_ms": _nested(
                            research.module_summaries,
                            "technical",
                            "lstm_latency_ms",
                        ),
                    },
                ),
                StructuredReportSection(
                    "行情",
                    research.module_summaries.get("market", {}),
                ),
                StructuredReportSection(
                    "供应链",
                    research.module_summaries.get("supply_chain", {}),
                ),
                StructuredReportSection(
                    "新闻",
                    research.module_summaries.get("news", {}),
                ),
                StructuredReportSection(
                    "风险",
                    research.module_summaries.get("risk", {}),
                ),
            ),
        )
        warnings: tuple[str, ...] = ()
        if self._model_gateway is not None and self._skill_gateway is not None:
            try:
                react_result = await ReActLoop(
                    self._model_gateway,
                    self._skill_gateway,
                    limits=ReActLimits(max_iterations=3),
                    observer=self._observer,
                ).run(
                    system_prompt=(
                        "你是投研报告叙述生成器。只能使用 Final Answer，"
                        "不得编造 Observation 中不存在的数字。"
                    ),
                    user_prompt=_react_report_prompt(report),
                    agent=self.manifest.name,
                    task_id=context.task_id,
                    scopes=context.scopes,
                    allowed_skills=frozenset(),
                    model=self._model_alias,
                    tenant_id=context.tenant_id,
                    user_id=context.user_id,
                )
                report = replace(
                    report,
                    narrative=react_result.final_answer,
                    react_trace=_react_trace_payload(react_result),
                )
            except Exception as exc:
                warnings = (
                    f"react report failed, using deterministic report: {type(exc).__name__}",
                )

        return AgentResult(
            agent=self.manifest.name,
            status="COMPLETED",
            data={"result": report},
            module_versions={"report": REPORT_VERSION},
            warnings=warnings,
        )


class StructuredReviewAgent:
    """对结构化报告做确定性质量与风险审核，模型只提供备注。"""

    _manifest = AgentManifest(
        name="review",
        version=REVIEW_VERSION,
        description="结构化报告质量与风险审核，模型仅提供备注",
        execution_type="model_driven",
        required_scopes=frozenset({"report.review"}),
        allowed_skills=frozenset(),
        external_model_allowed=True,
        side_effect="NONE",
        dependencies=("report",),
    )

    def __init__(
        self,
        *,
        model_gateway: ModelGateway | None = None,
        skill_gateway: SkillGateway | None = None,
        observer: ReActObserver | None = None,
        model_alias: str = "research",
    ) -> None:
        self._model_gateway = model_gateway
        self._skill_gateway = skill_gateway
        self._observer = observer
        self._model_alias = model_alias

    @property
    def manifest(self) -> AgentManifest:
        return self._manifest

    async def run(self, context: AgentContext) -> AgentResult:
        report = _result(context, "report")
        if report is None:
            return AgentResult(
                agent=self.manifest.name,
                status="FAILED",
                data={"error": "report result is missing"},
            )

        decision, reason = _review_report(report)
        review = StructuredReviewResult(
            decision=decision,
            reason=reason,
            report_summary=report.summary,
        )
        warnings: tuple[str, ...] = ()
        if self._model_gateway is not None and self._skill_gateway is not None:
            try:
                react_result = await ReActLoop(
                    self._model_gateway,
                    self._skill_gateway,
                    limits=ReActLimits(max_iterations=3),
                    observer=self._observer,
                ).run(
                    system_prompt=(
                        "你是投研审核助手。审核决策必须保持确定性结果，"
                        "你只能生成 review_note，不得改变 decision。"
                    ),
                    user_prompt=_react_review_prompt(report, decision, reason),
                    agent=self.manifest.name,
                    task_id=context.task_id,
                    scopes=context.scopes,
                    allowed_skills=frozenset(),
                    model=self._model_alias,
                    tenant_id=context.tenant_id,
                    user_id=context.user_id,
                )
                review = replace(
                    review,
                    review_note=react_result.final_answer,
                    react_trace=_react_trace_payload(react_result),
                )
            except Exception as exc:
                warnings = (
                    f"react review failed, using deterministic review: {type(exc).__name__}",
                )

        return AgentResult(
            agent=self.manifest.name,
            status="COMPLETED",
            data={"result": review},
            module_versions={"review": REVIEW_VERSION},
            warnings=warnings,
        )


def _result(context: AgentContext, name: str) -> Any | None:
    results = context.state.get("results") or {}
    agent_result = results.get(name)
    if agent_result is None or agent_result.status != "COMPLETED":
        return None
    data = getattr(agent_result, "data", {}) or {}
    return data.get("result")


def _review_report(report: Any) -> tuple[str, str]:
    if not report.sections:
        return "REJECTED", "报告缺少章节"

    risk_section = next(
        (section for section in report.sections if section.title == "风险"),
        None,
    )
    if risk_section is None:
        return "NEEDS_REVISION", "报告缺少风险章节"

    risk_level = risk_section.data.get("risk_level")
    if risk_level in (None, "UNKNOWN"):
        return "NEEDS_REVISION", "风险等级未知"
    if risk_level == "HIGH":
        return "NEEDS_REVISION", "风险等级为 HIGH"
    return "APPROVED", "报告审核通过"


def _nested(
    data: dict[str, Any],
    section: str,
    key: str,
) -> Any:
    return data.get(section, {}).get(key)


def _react_report_prompt(report: StructuredReportResult) -> str:
    payload = {
        "symbol": report.symbol,
        "summary": report.summary,
        "sections": [
            {"title": section.title, "data": section.data}
            for section in report.sections
        ],
    }
    return json.dumps(payload, ensure_ascii=False, default=str)


def _react_review_prompt(
    report: StructuredReportResult,
    decision: str,
    reason: str,
) -> str:
    payload = {
        "symbol": report.symbol,
        "decision": decision,
        "reason": reason,
        "report_summary": report.summary,
        "sections": [
            {"title": section.title, "data": section.data}
            for section in report.sections
        ],
    }
    return json.dumps(payload, ensure_ascii=False, default=str)


def _react_trace_payload(result: Any) -> dict[str, Any]:
    return {
        "final_answer": result.final_answer,
        "model_calls": result.model_calls,
        "steps": [
            {
                "step": step.step,
                "thought": step.thought,
                "action": step.action,
                "action_args": step.action_args,
                "observation": step.observation,
            }
            for step in result.steps
        ],
    }
