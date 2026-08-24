from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.market.store import MarketBarStore
from stock_research.stores.models.market import MarketBar


class MarketBarService:
    def __init__(self, session: AsyncSession) -> None:
        self.store = MarketBarStore(session)

    async def bars(
        self,
        symbol: str,
        period: str = "1m",
        limit: int = 100,
    ) -> list[MarketBar]:
        return await self.store.latest(symbol, period, limit)
