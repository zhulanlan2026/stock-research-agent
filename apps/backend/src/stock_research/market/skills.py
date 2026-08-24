from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.market.analysis import MarketAnalysisService, MarketSnapshotSummary
from stock_research.market.cache import MarketSnapshotCache


@dataclass(frozen=True)
class SkillManifest:
    name: str
    version: str
    execution_type: str
    required_scopes: tuple[str, ...]
    external_model_allowed: bool
    side_effect: str


@dataclass(frozen=True)
class StockIdentityResult:
    canonical_symbol: str
    market: str
    currency: str
    status: str


@dataclass(frozen=True)
class RealtimeSnapshotResult:
    symbol: str
    as_of: datetime | None
    summary: MarketSnapshotSummary
    stale: bool


class StockIdentitySkill:
    """确定性股票标识规范化 Skill，不调用外部模型。"""

    manifest = SkillManifest(
        name="stock_identity",
        version="1.0.0",
        execution_type="deterministic_engine",
        required_scopes=("skill.market.execute",),
        external_model_allowed=False,
        side_effect="NONE",
    )

    def execute(self, symbol: str) -> StockIdentityResult:
        raw = symbol.strip().upper()
        if "." in raw:
            code, market = raw.rsplit(".", 1)
        elif raw.endswith(("SH", "SZ", "BJ")) and len(raw) > 2:
            code, market = raw[:-2], raw[-2:]
        else:
            raise ValueError(f"unsupported stock identity: {symbol}")

        if not code.isdigit() or len(code) != 6:
            raise ValueError(f"unsupported stock code: {code}")

        market_map = {"SH": "上海证券交易所", "SZ": "深圳证券交易所", "BJ": "北京证券交易所"}
        if market not in market_map:
            raise ValueError(f"unsupported market: {market}")

        return StockIdentityResult(
            canonical_symbol=f"{code}.{market}",
            market=market_map[market],
            currency="CNY",
            status="ACTIVE",
        )


class RealtimeSnapshotSkill:
    """实时快照 Skill，返回 PostgreSQL 确定性摘要并标记 stale。"""

    manifest = SkillManifest(
        name="realtime_snapshot",
        version="1.0.0",
        execution_type="deterministic_engine",
        required_scopes=("skill.market.execute",),
        external_model_allowed=False,
        side_effect="NONE",
    )

    def __init__(
        self,
        session: AsyncSession,
        *,
        cache: MarketSnapshotCache | None = None,
        stale_after_seconds: int = 60,
    ) -> None:
        self._service = MarketAnalysisService(session, cache=cache)
        self.stale_after_seconds = stale_after_seconds

    async def execute(
        self,
        symbol: str,
        *,
        now: datetime | None = None,
    ) -> RealtimeSnapshotResult:
        summary = await self._service.summarize(symbol)
        now = now or datetime.now(timezone.utc)
        stale = (
            summary.event_time is None
            or (now - summary.event_time).total_seconds() > self.stale_after_seconds
        )
        return RealtimeSnapshotResult(
            symbol=symbol,
            as_of=summary.event_time,
            summary=summary,
            stale=stale,
        )
