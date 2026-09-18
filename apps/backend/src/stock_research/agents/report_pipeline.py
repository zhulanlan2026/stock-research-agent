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
                    _with_conclusion({
                        "symbol": context.symbol,
                        "as_of": research.as_of.isoformat(),
                        "coverage": research.coverage,
                        "module_versions": dict(research.module_versions),
                        "risk_level": _nested(
                            research.module_summaries,
                            "risk",
                            "risk_level",
                        ),
                    }, "概览"),
                ),
                StructuredReportSection(
                    "财务",
                    _with_conclusion(
                        research.module_summaries.get("fundamental", {}),
                        "财务",
                    ),
                ),
                StructuredReportSection(
                    "技术",
                    _with_conclusion(
                        research.module_summaries.get("technical", {}),
                        "技术",
                    ),
                ),
                StructuredReportSection(
                    "周期分析",
                    _with_conclusion({
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
                    }, "周期分析"),
                ),
                StructuredReportSection(
                    "行情",
                    _with_conclusion(
                        research.module_summaries.get("market", {}),
                        "行情",
                    ),
                ),
                StructuredReportSection(
                    "供应链",
                    _with_conclusion(
                        research.module_summaries.get("supply_chain", {}),
                        "供应链",
                    ),
                ),
                StructuredReportSection(
                    "新闻",
                    _with_conclusion(
                        research.module_summaries.get("news", {}),
                        "新闻",
                    ),
                ),
                StructuredReportSection(
                    "风险",
                    _with_conclusion(
                        research.module_summaries.get("risk", {}),
                        "风险",
                    ),
                ),
                StructuredReportSection(
                    "版本信息",
                    {
                        "report_version": REPORT_VERSION,
                        "module_versions": dict(research.module_versions),
                    },
                ),
                StructuredReportSection(
                    "免责声明",
                    {
                        "disclaimer": (
                            "本报告由系统基于结构化数据和文档证据自动生成，"
                            "仅供研究参考，不构成任何投资建议。"
                            "最终发布前必须经过人工审核。"
                        ),
                    },
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


def _with_conclusion(data: dict[str, Any], title: str) -> dict[str, Any]:
    return {**data, "conclusion": _section_conclusion(title, data)}


def _section_conclusion(title: str, data: dict[str, Any]) -> str:
    if title == "概览":
        risk_level = data.get("risk_level")
        coverage = data.get("coverage")
        risk_text = _risk_zh(risk_level)
        coverage_text = _percent_text(coverage)
        return f"综合风险等级为{risk_text}，数据覆盖度约{coverage_text}。"

    if title == "财务":
        roe = data.get("roe")
        net_margin = data.get("net_margin")
        parts = []
        if roe is not None:
            parts.append(f"ROE约{_percent_text(roe)}")
        if net_margin is not None:
            parts.append(f"净利率约{_percent_text(net_margin)}")
        if parts:
            return "财务表现：" + "，".join(parts) + "。"
        return "当前财务事实覆盖不足，暂无法形成可靠财务结论。"

    if title == "技术":
        latest_close = data.get("latest_close")
        rsi = data.get("rsi")
        macd_dif = data.get("macd_dif")
        macd_dea = data.get("macd_dea")
        if latest_close is None and rsi is None:
            return "当前技术指标数据不足，暂无法形成可靠技术结论。"
        parts = []
        if latest_close is not None:
            parts.append(f"最新收盘价约{latest_close}")
        if rsi is not None:
            parts.append(f"RSI约{rsi:.2f}")
        if macd_dif is not None and macd_dea is not None:
            if macd_dif > macd_dea:
                parts.append("MACD处于多头形态")
            else:
                parts.append("MACD处于空头或弱势形态")
        return "技术面：" + "，".join(parts) + "。"

    if title == "周期分析":
        periods = data.get("fft_periods") or []
        lstm_available = data.get("lstm_available")
        if periods:
            first_period = periods[0].get("period_bars")
            return (
                f"价格序列主要周期约为{first_period}根K线，"
                f"LSTM预测可用性：{bool(lstm_available)}。"
            )
        return "当前周期分析样本不足或未启用LSTM。"

    if title == "行情":
        last_price = data.get("last_price")
        change_pct = data.get("change_pct")
        if last_price is None:
            return "当前行情快照数据不足。"
        change_text = _percent_text(change_pct) if change_pct is not None else "未知"
        return f"最新价约{last_price}，涨跌幅约{change_text}。"

    if title == "供应链":
        nodes = data.get("nodes") or []
        edges = data.get("edges") or []
        if not edges:
            return "当前供应链图谱证据不足，暂无法形成供应链结论。"
        return f"供应链图谱包含{len(nodes)}个节点、{len(edges)}条关系边。"

    if title == "新闻":
        item_count = data.get("item_count")
        if item_count is None:
            return "当前没有足够的公告或新闻事件。"
        return f"近期共读取到{item_count}条公告/新闻事件。"

    if title == "风险":
        risk_level = data.get("risk_level")
        risk_score = data.get("risk_score")
        return f"风险等级为{_risk_zh(risk_level)}，风险评分约{risk_score}。"

    return "该维度暂无额外中文结论。"


def _risk_zh(value: Any) -> str:
    return {
        "LOW": "低风险",
        "MEDIUM": "中等风险",
        "HIGH": "高风险",
        "UNKNOWN": "风险未知",
    }.get(str(value), "风险未知")


def _percent_text(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "未知"
    return f"{number:.1%}"


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
