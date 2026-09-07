import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from stock_research.fundamental.schemas import FinancialFactCreate
from stock_research.fundamental.store import FinancialFactStore
from stock_research.stores.session import session_factory

METRICS = {
    "revenue": "1200.00",
    "cost_of_revenue": "450.00",
    "net_income": "250.00",
    "total_assets": "2500.00",
    "total_liabilities": "900.00",
    "total_equity": "1600.00",
    "current_assets": "700.00",
    "current_liabilities": "320.00",
    "operating_cash_flow": "300.00",
}


async def main() -> None:
    async with session_factory() as session:
        store = FinancialFactStore(session)
        for metric, value in METRICS.items():
            await store.upsert(
                FinancialFactCreate(
                    symbol="600519.SH",
                    metric=metric,
                    period="2025Q4",
                    value=Decimal(value),
                    unit="CNY",
                    source_id="demo",
                    disclosed_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
                    available_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
                )
            )
        await session.commit()
        print("seeded financial facts for 600519.SH")


if __name__ == "__main__":
    asyncio.run(main())
