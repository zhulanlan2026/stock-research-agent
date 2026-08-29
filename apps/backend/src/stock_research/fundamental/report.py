from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

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


def _valuation_data(valuation: ValuationSnapshot) -> dict[str, Any]:
    return {
        "price": _decimal_str(valuation.price),
        "eps": _decimal_str(valuation.per_share["eps"]),
        "pe": _decimal_str(valuation.multiples["pe"]),
        "pb": _decimal_str(valuation.multiples["pb"]),
        "ps": _decimal_str(valuation.multiples["ps"]),
        "market_cap": _decimal_str(valuation.market_cap),
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
