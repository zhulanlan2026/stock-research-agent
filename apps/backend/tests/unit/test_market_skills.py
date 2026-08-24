from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from stock_research.market.skills import RealtimeSnapshotSkill, StockIdentitySkill
from stock_research.stores.models.workflow import InboxEvent


def test_stock_identity_skill_normalizes_symbol() -> None:
    result = StockIdentitySkill().execute("600519.SH")

    assert result.canonical_symbol == "600519.SH"
    assert result.market == "上海证券交易所"
    assert result.currency == "CNY"


@pytest.mark.parametrize("symbol", ["ABC", "600519.XX", "600519"])
def test_stock_identity_skill_rejects_invalid(symbol: str) -> None:
    with pytest.raises(ValueError):
        StockIdentitySkill().execute(symbol)


async def test_realtime_snapshot_skill_marks_fresh_and_stale(db_context: Any) -> None:
    async with db_context.factory() as session:
        session.add(
            InboxEvent(
                event_id="snap-skill-1",
                event_type="market.snapshot",
                payload={"symbol": "600519.SH", "time": 1703228400000, "lastPrice": 9.2},
                received_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

        from stock_research.market.consumer import MarketDataConsumer

        await MarketDataConsumer(session).consume_pending()

        stale_skill = RealtimeSnapshotSkill(session, stale_after_seconds=1)
        stale_now = datetime.fromtimestamp(1703228400, tz=timezone.utc) + timedelta(seconds=120)
        stale_result = await stale_skill.execute("600519.SH", now=stale_now)
        assert stale_result.stale is True

        fresh_now = datetime.fromtimestamp(1703228400, tz=timezone.utc)
        fresh_result = await stale_skill.execute("600519.SH", now=fresh_now)
        assert fresh_result.stale is False
