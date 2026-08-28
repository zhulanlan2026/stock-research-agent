from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from stock_research.fundamental.engine import FundamentalSnapshot
from stock_research.fundamental.peer import (
    PeerEngine,
    _compute_peer_ranks,
    _peer_rank,
)
from stock_research.fundamental.schemas import FinancialFactCreate
from stock_research.fundamental.store import FinancialFactStore


def _snapshot(symbol: str, roe: Decimal | None) -> FundamentalSnapshot:
    return FundamentalSnapshot(
        symbol=symbol,
        as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
        module_version="fundamental:1.0.0",
        data_versions={},
        metrics={"net_income": None, "total_equity": None},
        ratios={
            "roe": roe,
            "gross_margin": None,
            "net_margin": None,
            "roa": None,
            "debt_to_equity": None,
            "current_ratio": None,
            "operating_cash_flow_to_net_income": None,
        },
        coverage=Decimal("0"),
    )


def test_peer_rank_is_deterministic_and_handles_missing_values() -> None:
    assert _peer_rank(Decimal("0.2"), [Decimal("0.1"), Decimal("0.3")]) == Decimal("0.5")
    assert _peer_rank(Decimal("0.2"), []) is None
    assert _peer_rank(None, [Decimal("0.1")]) is None
    assert _peer_rank(Decimal("0.2"), [None, Decimal("0.1")]) == Decimal("1")


def test_compute_peer_ranks_uses_only_peers() -> None:
    subject = _snapshot("subject", Decimal("0.2"))
    peers = {
        "peer-a": _snapshot("peer-a", Decimal("0.1")),
        "peer-b": _snapshot("peer-b", Decimal("0.3")),
    }

    ranks = _compute_peer_ranks(subject, peers)

    assert ranks["roe"] == Decimal("0.5")
    assert ranks["gross_margin"] is None


def _fact(symbol: str, metric: str, value: str) -> FinancialFactCreate:
    return FinancialFactCreate(
        symbol=symbol,
        metric=metric,
        period="2025Q4",
        value=Decimal(value),
        unit="CNY",
        source_id=f"source-{symbol}",
        disclosed_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        available_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
    )


async def test_peer_engine_compares_against_explicit_peers(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = FinancialFactStore(session)
        for symbol, net_income, total_equity in (
            ("600519.SH", "20.00", "100.00"),
            ("000858.SZ", "10.00", "100.00"),
            ("000568.SZ", "30.00", "100.00"),
        ):
            await store.upsert(_fact(symbol, "net_income", net_income))
            await store.upsert(_fact(symbol, "total_equity", total_equity))
        await session.commit()

        comparison = await PeerEngine(session).calculate(
            "600519.SH",
            ["000858.SZ", "000568.SZ"],
            datetime(2026, 4, 1, tzinfo=timezone.utc),
        )

        assert comparison.module_version == "peer:1.0.0"
        assert comparison.subject.symbol == "600519.SH"
        assert set(comparison.peers) == {"000858.SZ", "000568.SZ"}
        assert comparison.peer_ranks["roe"] == Decimal("0.5")


async def test_peer_engine_returns_none_rank_without_peer_values(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = FinancialFactStore(session)
        await store.upsert(_fact("600519.SH", "net_income", "20.00"))
        await store.upsert(_fact("600519.SH", "total_equity", "100.00"))
        await store.upsert(_fact("000858.SZ", "revenue", "50.00"))
        await session.commit()

        comparison = await PeerEngine(session).calculate(
            "600519.SH",
            ["000858.SZ"],
            datetime(2026, 4, 1, tzinfo=timezone.utc),
        )

        assert comparison.peer_ranks["roe"] is None
