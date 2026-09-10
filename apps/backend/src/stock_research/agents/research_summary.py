from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from stock_research.agents.protocol import (
    AgentContext,
    AgentManifest,
    AgentResult,
)
from stock_research.agents.react import ReActLimits, ReActLoop, ReActObserver
from stock_research.model_gateway.gateway import ModelGateway
from stock_research.skills.gateway import SkillGateway

RESEARCH_SUMMARY_VERSION = "research_summary:1.0.0"


@dataclass(frozen=True)
class ResearchSummaryResult:
    symbol: str
    as_of: datetime
    module_version: str
    status: str
    module_summaries: dict[str, dict[str, Any]]
    coverage: float
    summary_text: str
    react_trace: dict[str, Any] | None = None


class ResearchSummaryAgent:
    """汇总核心与风险 Agent 结果，形成结构化研究快照。

    默认走确定性汇总；注入 ModelGateway 和 SkillGateway 后，会额外使用受控
    ReAct 生成研究叙述，模型失败时回退到确定性摘要。
    """

    _manifest = AgentManifest(
        name="research",
        version=RESEARCH_SUMMARY_VERSION,
        description="汇总核心分析模块并生成研究快照",
        execution_type="model_driven",
        required_scopes=frozenset({"research.standard.execute"}),
        allowed_skills=frozenset({"research.context.read"}),
        external_model_allowed=True,
        side_effect="NONE",
        dependencies=(
            "fundamental",
            "technical",
            "market",
            "supply_chain",
            "news",
            "risk",
        ),
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
        summary = self._build_deterministic_summary(context)
        warnings: tuple[str, ...] = ()
        if self._model_gateway is not None and self._skill_gateway is not None:
            try:
                react_result = await ReActLoop(
                    self._model_gateway,
                    self._skill_gateway,
                    limits=ReActLimits(max_iterations=5),
                    observer=self._observer,
                ).run(
                    system_prompt=(
                        "你是投研汇总智能体。你只能使用 "
                        "Thought/Action/Observation 或 Final Answer。"
                        "所有数字必须来自 Observation，不得编造。"
                    ),
                    user_prompt=_react_prompt(context, summary),
                    agent=self.manifest.name,
                    task_id=context.task_id,
                    scopes=context.scopes,
                    allowed_skills=self.manifest.allowed_skills,
                    model=self._model_alias,
                    tenant_id=context.tenant_id,
                    user_id=context.user_id,
                )
                summary = replace(
                    summary,
                    summary_text=react_result.final_answer,
                    react_trace=_react_trace_payload(react_result),
                )
            except Exception as exc:
                warnings = (
                    f"react research failed, using deterministic summary: {type(exc).__name__}",
                )

        return AgentResult(
            agent=self.manifest.name,
            status="COMPLETED",
            data={"result": summary},
            module_versions={"research_summary": RESEARCH_SUMMARY_VERSION},
            warnings=warnings,
        )

    def _build_deterministic_summary(
        self,
        context: AgentContext,
    ) -> ResearchSummaryResult:
        results = context.state.get("results") or {}
        module_summaries = {
            name: _summarize_agent(name, results.get(name))
            for name in self.manifest.dependencies
        }
        coverage = _coverage(module_summaries)
        return ResearchSummaryResult(
            symbol=context.symbol,
            as_of=context.as_of or datetime.now().astimezone(),
            module_version=RESEARCH_SUMMARY_VERSION,
            status="COMPLETED",
            module_summaries=module_summaries,
            coverage=coverage,
            summary_text=_summary_text(context.symbol, module_summaries),
        )


def _summarize_agent(name: str, agent_result: Any) -> dict[str, Any]:
    if agent_result is None or agent_result.status != "COMPLETED":
        return {"status": "MISSING"}

    data = getattr(agent_result, "data", {}) or {}
    result = data.get("result")
    if result is None:
        return {"status": "EMPTY"}

    summarizers = {
        "fundamental": _summarize_fundamental,
        "technical": _summarize_technical,
        "market": _summarize_market,
        "supply_chain": _summarize_supply_chain,
        "news": _summarize_news,
        "risk": _summarize_risk,
    }
    summarizer = summarizers.get(name)
    if summarizer is None:
        return {"status": "UNSUPPORTED"}
    return {"status": "COMPLETED", **_jsonable(summarizer(result))}


def _summarize_fundamental(snapshot: Any) -> dict[str, Any]:
    metrics = getattr(snapshot, "metrics", {}) or {}
    ratios = getattr(snapshot, "ratios", {}) or {}
    return {
        "module_version": getattr(snapshot, "module_version", None),
        "coverage": _decimal_text(getattr(snapshot, "coverage", None)),
        "revenue": _decimal_text(metrics.get("revenue")),
        "net_income": _decimal_text(metrics.get("net_income")),
        "roe": _decimal_text(ratios.get("roe")),
        "net_margin": _decimal_text(ratios.get("net_margin")),
    }


def _summarize_technical(result: Any) -> dict[str, Any]:
    points = getattr(result, "points", []) or []
    latest = points[-1] if points else None
    cycle_analysis = getattr(result, "cycle_analysis", None)
    return {
        "module_version": getattr(result, "module_version", None),
        "period": getattr(result, "period", None),
        "point_count": len(points),
        "latest_time": latest.time.isoformat() if latest else None,
        "latest_close": getattr(latest, "close", None) if latest else None,
        "rsi": getattr(latest, "rsi", None) if latest else None,
        "macd_dif": getattr(latest, "macd_dif", None) if latest else None,
        "macd_dea": getattr(latest, "macd_dea", None) if latest else None,
        "macd_hist": getattr(latest, "macd_hist", None) if latest else None,
        "fft_periods": _cycle_fft_periods(cycle_analysis),
        "wavelet_energy": _cycle_wavelet_energy(cycle_analysis),
        "lstm_available": _cycle_lstm_available(cycle_analysis),
        "lstm_latency_ms": _cycle_lstm_latency_ms(cycle_analysis),
    }


def _cycle_fft_periods(cycle_analysis: Any) -> list[dict[str, Any]]:
    periods = getattr(cycle_analysis, "fft_periods", ()) or ()
    return [dict(period) for period in periods]


def _cycle_wavelet_energy(cycle_analysis: Any) -> list[dict[str, Any]]:
    energy = getattr(cycle_analysis, "wavelet_energy", ()) or ()
    return [dict(level) for level in energy]


def _cycle_lstm_available(cycle_analysis: Any) -> bool:
    return bool(getattr(cycle_analysis, "lstm_available", False))


def _cycle_lstm_latency_ms(cycle_analysis: Any) -> int | None:
    return getattr(cycle_analysis, "lstm_latency_ms", None)


def _summarize_market(result: Any) -> dict[str, Any]:
    summary = getattr(result, "summary", None)
    return {
        "module_version": getattr(result, "module_version", None),
        "last_price": getattr(summary, "last_price", None) if summary else None,
        "change_pct": getattr(summary, "change_pct", None) if summary else None,
        "sample_count": getattr(summary, "sample_count", 0) if summary else 0,
    }


def _summarize_risk(snapshot: Any) -> dict[str, Any]:
    market_risk = getattr(snapshot, "market_risk", {}) or {}
    return {
        "module_version": getattr(snapshot, "module_version", None),
        "risk_level": getattr(snapshot, "risk_level", None),
        "risk_action": getattr(snapshot, "risk_action", None),
        "risk_score": _decimal_text(getattr(snapshot, "risk_score", None)),
        "coverage": _decimal_text(getattr(snapshot, "coverage", None)),
        "annualized_volatility": _decimal_text(
            market_risk.get("annualized_volatility")
        ),
        "max_drawdown": _decimal_text(market_risk.get("max_drawdown")),
    }


def _summarize_supply_chain(snapshot: Any) -> dict[str, Any]:
    return {
        "module_version": getattr(snapshot, "module_version", None),
        "node_count": len(getattr(snapshot, "nodes", ()) or ()),
        "edge_count": len(getattr(snapshot, "edges", ()) or ()),
    }


def _summarize_news(snapshot: Any) -> dict[str, Any]:
    return {
        "module_version": getattr(snapshot, "module_version", None),
        "query": getattr(snapshot, "query", None),
        "item_count": len(getattr(snapshot, "items", ()) or ()),
    }


def _coverage(module_summaries: dict[str, dict[str, Any]]) -> float:
    completed = [
        summary
        for summary in module_summaries.values()
        if summary.get("status") == "COMPLETED"
    ]
    if not module_summaries:
        return 0.0
    return len(completed) / len(module_summaries)


def _summary_text(symbol: str, module_summaries: dict[str, dict[str, Any]]) -> str:
    risk = module_summaries.get("risk", {})
    market = module_summaries.get("market", {})
    risk_level = risk.get("risk_level") or "UNKNOWN"
    change_pct = market.get("change_pct")
    change_text = (
        f"{change_pct:.2f}%" if isinstance(change_pct, (int, float)) else "暂无"
    )
    return f"{symbol} 风险等级 {risk_level}，行情涨跌幅 {change_text}。"


def _react_prompt(context: AgentContext, summary: ResearchSummaryResult) -> str:
    payload = {
        "symbol": context.symbol,
        "question": context.purpose,
        "deterministic_summary": summary.module_summaries,
        "coverage": summary.coverage,
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


def _decimal_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return str(value)
