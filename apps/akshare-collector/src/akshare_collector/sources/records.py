from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BarRecord:
    symbol: str
    period: str
    time_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float | None
    amount: float | None


@dataclass(frozen=True)
class QuoteRecord:
    symbol: str
    time_ms: int
    fields: dict[str, object]


@dataclass(frozen=True)
class AnnouncementRecord:
    symbol: str
    time_ms: int
    headline: str | None
    url: str | None
    source: str | None
