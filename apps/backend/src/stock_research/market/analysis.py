from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.market.cache import MarketSnapshotCache
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
    def __init__(
        self,
        session: AsyncSession,
        *,
        cache: MarketSnapshotCache | None = None,
    ) -> None:
        self.store = MarketSnapshotStore(session)
        self.cache = cache

    async def summarize(self, symbol: str, limit: int = 20) -> MarketSnapshotSummary:
        if self.cache is not None:
            try:
                cached = await self.cache.get_summary(symbol)
            except Exception:
                cached = None
            if cached is not None:
                return _summary_from_cache(symbol, cached)

        snapshots = await self.store.latest(symbol, limit)
        summary = summarize_snapshots(symbol, snapshots)

        if self.cache is not None:
            try:
                await self.cache.set_summary(symbol, _summary_to_cache(summary))
            except Exception:
                pass
        return summary


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


def _summary_to_cache(summary: MarketSnapshotSummary) -> dict[str, Any]:
    return {
        "symbol": summary.symbol,
        "last_price": summary.last_price,
        "previous_close": summary.previous_close,
        "change": summary.change,
        "change_pct": summary.change_pct,
        "bid_ask_spread": summary.bid_ask_spread,
        "event_time": summary.event_time.isoformat() if summary.event_time is not None else None,
        "sample_count": summary.sample_count,
    }


def _summary_from_cache(symbol: str, cached: dict[str, Any]) -> MarketSnapshotSummary:
    event_time_raw = cached.get("event_time")
    event_time = (
        datetime.fromisoformat(event_time_raw)
        if isinstance(event_time_raw, str)
        else None
    )
    return MarketSnapshotSummary(
        symbol=str(cached.get("symbol") or symbol),
        last_price=_optional_float_from_cache(cached.get("last_price")),
        previous_close=_optional_float_from_cache(cached.get("previous_close")),
        change=_optional_float_from_cache(cached.get("change")),
        change_pct=_optional_float_from_cache(cached.get("change_pct")),
        bid_ask_spread=_optional_float_from_cache(cached.get("bid_ask_spread")),
        event_time=event_time,
        sample_count=int(cached.get("sample_count") or 0),
    )


def _optional_float_from_cache(value: object | None) -> float | None:
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)
