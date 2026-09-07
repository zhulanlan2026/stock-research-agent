from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from stock_research.fundamental.engine import FundamentalSnapshot
from stock_research.fundamental.peer import PeerComparison
from stock_research.fundamental.research import StandardResearchResult
from stock_research.fundamental.risk import RiskSnapshot
from stock_research.fundamental.scenario import ScenarioSnapshot
from stock_research.fundamental.valuation import ValuationSnapshot

REPORT_SERVICE_VERSION = "report:1.0.0"


@dataclass(frozen=True)
class ReportSection:
    title: str
    data: dict[str, Any]


@dataclass(frozen=True)
class ReportResult:
    symbol: str
    as_of: datetime
    module_version: str
    summary: str
    sections: list[ReportSection]


class ReportService:
    """从标准研究结果确定性渲染结构化报告。"""

    module_version = REPORT_SERVICE_VERSION

    def render(self, result: StandardResearchResult) -> ReportResult:
        snapshot = result.snapshot
        return ReportResult(
            symbol=result.symbol,
            as_of=result.as_of,
            module_version=self.module_version,
            summary=_chinese_summary(result),
            sections=[
                ReportSection(
                    "概览",
                    {
                        "risk_level": snapshot.risk.risk_level,
                        "decision": snapshot.decision.decision
                        if snapshot.decision is not None
                        else "INSUFFICIENT_DATA",
                        "coverage": str(result.coverage),
                    },
                ),
                ReportSection(
                    "财务",
                    _fundamental_data(snapshot.fundamental),
                ),
                ReportSection(
                    "估值",
                    _valuation_data(snapshot.valuation),
                ),
                ReportSection(
                    "情景",
                    _scenario_data(snapshot.scenario),
                ),
                ReportSection(
                    "风险",
                    _risk_data(snapshot.risk),
                ),
                ReportSection(
                    "同业",
                    _peer_data(result.peer_comparison),
                ),
            ],
        )


_RISK_ZH = {
    "HIGH": "高风险",
    "MEDIUM": "中等风险",
    "LOW": "低风险",
    "UNKNOWN": "风险未知",
}
_DECISION_ZH = {
    "AVOID": "规避",
    "HOLD": "持有观望",
    "ATTRACTIVE": "具备吸引力",
    "INSUFFICIENT_DATA": "数据不足，暂无法判断",
}


def _chinese_summary(result: StandardResearchResult) -> str:
    snapshot = result.snapshot
    risk_level = snapshot.risk.risk_level
    decision = (
        snapshot.decision.decision
        if snapshot.decision is not None
        else "INSUFFICIENT_DATA"
    )

    parts = [
        f"{result.symbol} 当前为{_RISK_ZH.get(risk_level, risk_level)}，"
        f"综合决策建议「{_DECISION_ZH.get(decision, decision)}」。"
    ]

    pe = snapshot.valuation.multiples.get("pe")
    if pe is not None:
        parts.append(f"市盈率（PE）约 {pe:.2f} 倍。")

    net_income = snapshot.fundamental.metrics.get("net_income")
    if net_income is not None:
        parts.append(f"净利润 {net_income} 元。")
    roe = snapshot.fundamental.ratios.get("roe")
    if roe is not None:
        parts.append(f"净资产收益率（ROE）约 {roe:.2%}。")

    scenario = snapshot.scenario
    if scenario is not None:
        base = next(
            (point for point in scenario.scenarios if point.name == "BASE"),
            None,
        )
        if base is not None and base.target_price is not None:
            parts.append(f"基准情景目标价 {base.target_price} 元。")

    parts.append(f"数据覆盖度 {result.coverage:.0%}。")
    return "".join(parts)


def _valuation_data(valuation: ValuationSnapshot) -> dict[str, Any]:
    return {
        "price": _decimal_str(valuation.price),
        "eps": _decimal_str(valuation.per_share["eps"]),
        "pe": _decimal_str(valuation.multiples["pe"]),
        "pb": _decimal_str(valuation.multiples["pb"]),
        "ps": _decimal_str(valuation.multiples["ps"]),
        "market_cap": _decimal_str(valuation.market_cap),
    }


def _fundamental_data(fundamental: FundamentalSnapshot) -> dict[str, Any]:
    return {
        "营收": _decimal_str(fundamental.metrics["revenue"]),
        "净利润": _decimal_str(fundamental.metrics["net_income"]),
        "总资产": _decimal_str(fundamental.metrics["total_assets"]),
        "总负债": _decimal_str(fundamental.metrics["total_liabilities"]),
        "总权益": _decimal_str(fundamental.metrics["total_equity"]),
        "毛利率": _decimal_str(fundamental.ratios["gross_margin"]),
        "净利率": _decimal_str(fundamental.ratios["net_margin"]),
        "ROE": _decimal_str(fundamental.ratios["roe"]),
        "ROA": _decimal_str(fundamental.ratios["roa"]),
        "负债权益比": _decimal_str(fundamental.ratios["debt_to_equity"]),
        "流动比率": _decimal_str(fundamental.ratios["current_ratio"]),
        "现金流/净利润": _decimal_str(
            fundamental.ratios["operating_cash_flow_to_net_income"]
        ),
    }


def _scenario_data(scenario: ScenarioSnapshot | None) -> dict[str, Any]:
    if scenario is None:
        return {"scenarios": []}
    return {
        "scenarios": [
            {
                "name": point.name,
                "pe": _decimal_str(point.pe),
                "target_price": _decimal_str(point.target_price),
                "implied_return": _decimal_str(point.implied_return),
            }
            for point in scenario.scenarios
        ]
    }


def _risk_data(risk: RiskSnapshot) -> dict[str, Any]:
    return {
        "risk_level": risk.risk_level,
        "risk_score": _decimal_str(risk.risk_score),
        "financial_ratios": {
            key: _decimal_str(value)
            for key, value in risk.financial_ratios.items()
        },
        "market_risk": {
            key: _decimal_str(value)
            for key, value in risk.market_risk.items()
        },
    }


def _peer_data(peer: PeerComparison | None) -> dict[str, Any]:
    if peer is None:
        return {"peers": {}}
    return {
        "peers": list(peer.peers.keys()),
        "peer_ranks": {
            key: _decimal_str(value)
            for key, value in peer.peer_ranks.items()
        },
    }


def _decimal_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)
