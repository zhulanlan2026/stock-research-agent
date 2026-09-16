from datetime import datetime, timezone
from typing import Any

from stock_research.fundamental.consumer import FinancialFactConsumer
from stock_research.fundamental.store import FinancialFactStore
from stock_research.stores.models.workflow import InboxEvent


async def test_financial_fact_consumer_upserts_inbox_event(db_context: Any) -> None:
    async with db_context.factory() as session:
        session.add(
            InboxEvent(
                event_id="financial-1",
                event_type="financial.fact",
                payload={
                    "symbol": "600519.SH",
                    "metric": "revenue",
                    "period": "2025Q4",
                    "value": "1200.00",
                    "unit": "CNY",
                    "source_id": "real-financial-source",
                    "disclosed_at": 1767225600000,
                    "available_at": 1767225600000,
                },
            )
        )
        await session.commit()

        consumed = await FinancialFactConsumer(session).consume_pending()
        facts = await FinancialFactStore(session).list_for_symbol(
            symbol="600519.SH",
            as_of=datetime(2026, 1, 2, tzinfo=timezone.utc),
            metrics=["revenue"],
        )

    assert consumed == 1
    assert len(facts) == 1
    assert str(facts[0].value) == "1200.000000000000"
