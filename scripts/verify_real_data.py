import asyncio

from sqlalchemy import func, select

from stock_research.stores.models.fundamental import FinancialFact
from stock_research.stores.models.market import MarketBar, MarketNews
from stock_research.stores.models.workflow import InboxEvent
from stock_research.stores.session import engine, session_factory


async def main() -> None:
    async with session_factory() as session:
        inbox_total = (
            await session.execute(select(func.count()).select_from(InboxEvent))
        ).scalar_one()
        inbox_pending = (
            await session.execute(
                select(func.count())
                .select_from(InboxEvent)
                .where(InboxEvent.processed_at.is_(None))
            )
        ).scalar_one()
        news_count = (
            await session.execute(select(func.count()).select_from(MarketNews))
        ).scalar_one()
        financial_count = (
            await session.execute(select(func.count()).select_from(FinancialFact))
        ).scalar_one()

        print(f"inbox_event: total={inbox_total}, pending={inbox_pending}")
        print(f"market_news: {news_count}")
        print(f"financial_fact: {financial_count}")

        bars = (
            await session.execute(
                select(
                    MarketBar.symbol,
                    MarketBar.period,
                    func.count(),
                    func.max(MarketBar.bar_time),
                )
                .group_by(MarketBar.symbol, MarketBar.period)
                .order_by(MarketBar.symbol, MarketBar.period)
            )
        ).all()
        print("market_bar:")
        for symbol, period, count, latest in bars:
            print(f"  {symbol} {period}: count={count}, latest={latest}")

        latest_news = (
            await session.execute(select(func.max(MarketNews.event_time)))
        ).scalar_one()
        latest_financial = (
            await session.execute(select(func.max(FinancialFact.available_at)))
        ).scalar_one()
        print(f"market_news latest: {latest_news}")
        print(f"financial_fact latest: {latest_financial}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
