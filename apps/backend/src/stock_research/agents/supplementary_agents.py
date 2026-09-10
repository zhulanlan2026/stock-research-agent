from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from stock_research.agents.protocol import (
    AgentContext,
    AgentManifest,
    AgentResult,
)
from stock_research.market.store import MarketNewsStore
from stock_research.supply_chain.skill import SupplyChainSkill

NEWS_VERSION = "news:1.1.0"
SUPPLY_CHAIN_VERSION = "supply_chain:1.0.0"


@dataclass(frozen=True)
class NewsSnapshot:
    symbol: str
    as_of: datetime
    module_version: str
    query: str | None
    items: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class SupplyChainSnapshot:
    symbol: str
    as_of: datetime
    module_version: str
    nodes: tuple[str, ...]
    edges: tuple[dict[str, str], ...]


class NewsAgent:
    """新闻/事件 Agent，读取已落库的新闻与公告事实。

    未注入 session_factory 或库里暂无数据时返回空快照，不调用外部 API，
    也不通过模型虚构新闻。
    """

    _manifest = AgentManifest(
        name="news",
        version=NEWS_VERSION,
        description="市场新闻与事件结构化快照",
        execution_type="deterministic_engine",
        required_scopes=frozenset({"stock.market.read"}),
        allowed_skills=frozenset(),
        external_model_allowed=False,
        side_effect="NONE",
    )

    def __init__(self, session_factory: Any | None = None) -> None:
        self._session_factory = session_factory

    @property
    def manifest(self) -> AgentManifest:
        return self._manifest

    async def run(self, context: AgentContext) -> AgentResult:
        items = await self._load_items(context)
        snapshot = NewsSnapshot(
            symbol=context.symbol,
            as_of=context.as_of or datetime.now(timezone.utc),
            module_version=NEWS_VERSION,
            query=context.purpose,
            items=items,
        )
        return AgentResult(
            agent=self.manifest.name,
            status="COMPLETED",
            data={"result": snapshot},
            module_versions={"news": NEWS_VERSION},
        )

    async def _load_items(
        self,
        context: AgentContext,
    ) -> tuple[dict[str, Any], ...]:
        if self._session_factory is None:
            return ()

        limit = _int_state(context.state, "news_limit", 20)
        async with self._session_factory() as session:
            rows = await MarketNewsStore(session).latest(
                context.symbol,
                as_of=context.as_of,
                limit=limit,
            )
        return tuple(
            {
                "kind": row.kind,
                "event_time": row.event_time.isoformat(),
                "headline": row.headline,
                "url": row.url,
                "source_event_id": row.source_event_id,
                "payload": dict(row.payload or {}),
            }
            for row in rows
        )


class SupplyChainAgent:
    """将供应链 Skill 包装为多 Agent 节点。"""

    _manifest = AgentManifest(
        name="supply_chain",
        version=SUPPLY_CHAIN_VERSION,
        description="供应链关系抽取与图候选",
        execution_type="deterministic_engine",
        required_scopes=frozenset({"stock.supply_chain.read"}),
        allowed_skills=frozenset({"skill.supply_chain.execute"}),
        external_model_allowed=False,
        side_effect="NONE",
    )

    def __init__(self, skill: SupplyChainSkill | None = None) -> None:
        self._skill = skill or SupplyChainSkill()

    @property
    def manifest(self) -> AgentManifest:
        return self._manifest

    async def run(self, context: AgentContext) -> AgentResult:
        text = context.purpose or context.symbol
        candidate = self._skill.execute(text)
        snapshot = SupplyChainSnapshot(
            symbol=context.symbol,
            as_of=context.as_of or datetime.now(timezone.utc),
            module_version=SUPPLY_CHAIN_VERSION,
            nodes=tuple(candidate.nodes),
            edges=tuple(
                {"source": source, "predicate": predicate, "target": target}
                for source, predicate, target in candidate.edges
            ),
        )
        return AgentResult(
            agent=self.manifest.name,
            status="COMPLETED",
            data={"result": snapshot},
            module_versions={"supply_chain": SUPPLY_CHAIN_VERSION},
        )


def _int_state(state: Any, key: str, default: int) -> int:
    value = state.get(key)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
