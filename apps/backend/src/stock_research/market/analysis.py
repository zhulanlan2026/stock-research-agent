from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.market.store import MarketSnapshotStore
from stock_research.stores.models.market import MarketSnapshot


@dataclass(frozen=True)
class MarketSnapshotSummary:
    symbol: str
    last_price: float | None
    previous_close: float | None
    change: float | None
    change_pct: float | None
    bid_ask_spread: float | None
    event_time: datetime | None
    sample_count: int


class MarketAnalysisService:
    def __init__(self, session: AsyncSession) -> None:
        self.store = MarketSnapshotStore(session)

    async def summarize(self, symbol: str, limit: int = 20) -> MarketSnapshotSummary:
        snapshots = await self.store.latest(symbol, limit)
        return summarize_snapshots(symbol, snapshots)


def summarize_snapshots(
    symbol: str,
    snapshots: Sequence[MarketSnapshot],
) -> MarketSnapshotSummary:
    if not snapshots:
        return MarketSnapshotSummary(
            symbol=symbol,
            last_price=None,
            previous_close=None,
            change=None,
            change_pct=None,
            bid_ask_spread=None,
            event_time=None,
            sample_count=0,
        )

    latest = snapshots[0]
    last_price = _as_float(_first(latest.payload, "lastPrice", "last_price"))
    previous_close = _as_float(_first(latest.payload, "lastClose", "preClose"))
    change = (
        last_price - previous_close
        if last_price is not None and previous_close is not None
        else None
    )
    change_pct = (
        change / previous_close * 100
        if change is not None and previous_close is not None and previous_close != 0.0
        else None
    )
    bid_ask_spread = _bid_ask_spread(latest.payload)

    return MarketSnapshotSummary(
        symbol=symbol,
        last_price=last_price,
        previous_close=previous_close,
        change=_round_optional(change),
        change_pct=_round_optional(change_pct),
        bid_ask_spread=_round_optional(bid_ask_spread),
        event_time=latest.event_time,
        sample_count=len(snapshots),
    )


def _first(payload: dict[str, object], *keys: str) -> object | None:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _as_float(value: object | None) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _bid_ask_spread(payload: dict[str, object]) -> float | None:
    bid = _first_list_item(payload.get("bidPrice"))
    ask = _first_list_item(payload.get("askPrice"))
    if bid is None or ask is None:
        return None
    return ask - bid


def _round_optional(value: float | None, ndigits: int = 6) -> float | None:
    if value is None:
        return None
    return round(value, ndigits)


def _first_list_item(value: object | None) -> float | None:
    if isinstance(value, (list, tuple)) and value:
        return _as_float(value[0])
    return None
