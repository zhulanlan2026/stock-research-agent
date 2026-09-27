from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from akshare_collector.sources.records import AnnouncementRecord, BarRecord, QuoteRecord
from akshare_collector.sources.timeutil import utcnow_ms


@dataclass(frozen=True)
class CollectorEvent:
    event_id: str
    event_type: str
    payload: dict[str, object]


def _event_id(prefix: str, payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return f"{prefix}:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def normalize_bar(bar: BarRecord) -> CollectorEvent:
    payload: dict[str, object] = {
        "symbol": bar.symbol,
        "period": bar.period,
        "time": bar.time_ms,
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "volume": bar.volume,
        "amount": bar.amount,
    }
    return CollectorEvent(
        event_id=_event_id("bar", payload),
        event_type="market.bar",
        payload=payload,
    )


def normalize_quote(quote: QuoteRecord) -> CollectorEvent:
    payload: dict[str, object] = {"symbol": quote.symbol, "time": quote.time_ms}
    payload.update(quote.fields)
    return CollectorEvent(
        event_id=_event_id("quote", payload),
        event_type="market.quote",
        payload=payload,
    )


def normalize_announcement(record: AnnouncementRecord) -> CollectorEvent:
    payload: dict[str, object] = {
        "symbol": record.symbol,
        "kind": "announcement",
        "time": record.time_ms,
        "headline": record.headline,
        "url": record.url,
        "source": record.source,
    }
    return CollectorEvent(
        event_id=_event_id("announcement", payload),
        event_type="market.announcement",
        payload=payload,
    )


def normalize_financial_fact(raw: dict[str, object]) -> CollectorEvent:
    required = ("symbol", "metric", "period", "value", "source_id")
    missing = [key for key in required if not raw.get(key)]
    if missing:
        raise ValueError(f"missing financial fact fields: {', '.join(missing)}")

    payload: dict[str, object] = {
        "symbol": raw["symbol"],
        "metric": raw["metric"],
        "period": raw["period"],
        "value": raw["value"],
        "unit": raw.get("unit") or "CNY",
        "source_id": raw["source_id"],
        "disclosed_at": raw.get("disclosed_at") or utcnow_ms(),
        "available_at": raw.get("available_at") or raw.get("disclosed_at") or utcnow_ms(),
        "revision_no": raw.get("revision_no") or 1,
        "truth_status": raw.get("truth_status") or "VERIFIED",
        "metadata": raw.get("metadata") or {},
    }
    return CollectorEvent(
        event_id=_event_id("financial", payload),
        event_type="financial.fact",
        payload=payload,
    )
