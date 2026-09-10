from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

from stock_research.agents.engine_agents import (
    FundamentalEngineAgent,
    MarketEngineAgent,
    TechnicalEngineAgent,
    build_research_agents,
)
from stock_research.agents.orchestrator import AgentOrchestrator
from stock_research.agents.protocol import AgentContext
from stock_research.agents.registry import AgentRegistry


class _EngineResult:
    def __init__(self, module_version: str, symbol: str) -> None:
        self.module_version = module_version
        self.symbol = symbol


class _FakeFundamentalEngine:
    async def calculate(self, symbol: str, as_of: datetime) -> _EngineResult:
        return _EngineResult("fundamental:1.0.0", symbol)


class _FakeTechnicalEngine:
    async def calculate(self, symbol: str, **kwargs: Any) -> _EngineResult:
        return _EngineResult("technical:1.0.0", f"{symbol}:{kwargs.get('period')}")


class _FakeMarketEngine:
    async def calculate(self, symbol: str, limit: int = 20) -> _EngineResult:
        return _EngineResult("market:1.0.0", symbol)


async def test_core_engine_agents_run_through_langgraph_orchestrator() -> None:
    registry = AgentRegistry(
        [
            FundamentalEngineAgent(cast(Any, _FakeFundamentalEngine())),
            TechnicalEngineAgent(cast(Any, _FakeTechnicalEngine())),
            MarketEngineAgent(cast(Any, _FakeMarketEngine())),
        ]
    )
    orchestrator = AgentOrchestrator(registry, prefer_langgraph=True)

    result = await orchestrator.run(
        AgentContext(
            task_id="task-1",
            symbol="600519.SH",
            mode="standard",
            as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
            state={"technical_period": "1d"},
        ),
        ["fundamental", "technical", "market"],
    )

    assert set(result.results) == {"fundamental", "technical", "market"}
    assert result.state["fundamental"]["result"].module_version == "fundamental:1.0.0"
    assert result.state["technical"]["result"].symbol == "600519.SH:1d"
    assert result.state["market"]["result"].module_version == "market:1.0.0"


def test_research_agents_include_risk_dependency() -> None:
    agents = build_research_agents(object())
    manifests = {agent.manifest.name: agent.manifest for agent in agents}

    assert set(manifests) == {
        "fundamental",
        "technical",
        "market",
        "news",
        "supply_chain",
        "risk",
        "research",
        "report",
        "review",
    }
    assert manifests["risk"].dependencies == ("fundamental", "technical", "market")
    assert manifests["research"].dependencies == (
        "fundamental",
        "technical",
        "market",
        "supply_chain",
        "news",
        "risk",
    )
    assert manifests["news"].dependencies == ()
    assert manifests["supply_chain"].dependencies == ()
    assert manifests["report"].dependencies == ("research",)
    assert manifests["review"].dependencies == ("report",)
