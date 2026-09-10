from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from stock_research.agents import supplementary_agents
from stock_research.agents.protocol import AgentContext
from stock_research.agents.supplementary_agents import NewsAgent, SupplyChainAgent


async def test_news_agent_returns_empty_news_snapshot() -> None:
    context = AgentContext(
        task_id="task-1",
        symbol="600519.SH",
        mode="standard",
        as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
        purpose="近期新闻",
    )

    result = await NewsAgent().run(context)

    snapshot = result.data["result"]
    assert snapshot.symbol == "600519.SH"
    assert snapshot.items == ()


async def test_news_agent_loads_stored_news_facts(monkeypatch: Any) -> None:
    @dataclass
    class NewsRow:
        kind: str
        event_time: datetime
        headline: str | None
        url: str | None
        source_event_id: str
        payload: dict[str, Any]

    class NewsStore:
        def __init__(self, session: Any) -> None:
            self.session = session

        async def latest(
            self,
            symbol: str,
            *,
            as_of: datetime | None,
            limit: int,
        ) -> list[NewsRow]:
            assert symbol == "600519.SH"
            assert limit == 20
            return [
                NewsRow(
                    kind="announcement",
                    event_time=datetime(2026, 4, 1, tzinfo=timezone.utc),
                    headline="重大合同公告",
                    url="https://example.com/a",
                    source_event_id="evt-news-1",
                    payload={"title": "重大合同公告"},
                )
            ]

    news_store = NewsStore(object())
    monkeypatch.setattr(
        supplementary_agents,
        "MarketNewsStore",
        lambda session: news_store,
    )

    class Session:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, *args: Any) -> None:
            return None

    def session_factory() -> Session:
        return Session()

    context = AgentContext(
        task_id="task-1",
        symbol="600519.SH",
        mode="standard",
        as_of=datetime(2026, 4, 2, tzinfo=timezone.utc),
        purpose="近期公告",
        state={"news_limit": 20},
    )

    result = await NewsAgent(session_factory=session_factory).run(context)

    snapshot = result.data["result"]
    assert snapshot.items[0]["kind"] == "announcement"
    assert snapshot.items[0]["headline"] == "重大合同公告"


async def test_supply_chain_agent_extracts_graph_candidate() -> None:
    context = AgentContext(
        task_id="task-1",
        symbol="600519.SH",
        mode="standard",
        purpose="公司A与公司B签订合同",
    )

    result = await SupplyChainAgent().run(context)

    snapshot = result.data["result"]
    assert "公司A" in snapshot.nodes
    assert snapshot.edges[0]["predicate"] == "signed_contract_with"
