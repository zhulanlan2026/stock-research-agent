from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.core.config import get_settings
from stock_research.documents.draft import EvidenceClaimDraftStore
from stock_research.documents.store import NormalizedBlockStore
from stock_research.fundamental.engine import FundamentalEngine
from stock_research.fundamental.quality import QualityEngine
from stock_research.fundamental.risk import RiskEngine
from stock_research.fundamental.scenario import ScenarioAssumption, ScenarioEngine
from stock_research.fundamental.valuation import ValuationEngine
from stock_research.market.analysis import MarketAnalysisService
from stock_research.market.bar_service import MarketBarService
from stock_research.market.cycle import CycleAnalysisService
from stock_research.market.engine import MarketEngine, TechnicalEngine
from stock_research.market.store import (
    MarketNewsStore,
    MarketSnapshotStore,
)
from stock_research.supply_chain.neo4j_client import GraphData, Neo4jPublisher
from stock_research.supply_chain.store import SupplyChainStore


class MarketDataService:
    """统一市场行情、K线、新闻和技术面数据访问。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def snapshots(
        self,
        symbol: str,
        limit: int = 20,
        *,
        as_of: datetime | None = None,
    ) -> list[Any]:
        return await MarketSnapshotStore(self.session).latest(
            symbol,
            limit,
            as_of=as_of,
        )

    async def bars(
        self,
        symbol: str,
        period: str = "1d",
        limit: int = 100,
        *,
        as_of: datetime | None = None,
    ) -> list[Any]:
        return await MarketBarService(self.session).bars(
            symbol,
            period,
            limit,
            as_of=as_of,
        )

    async def news(
        self,
        symbol: str,
        *,
        as_of: datetime | None = None,
        limit: int = 20,
    ) -> list[Any]:
        return await MarketNewsStore(self.session).latest(
            symbol,
            as_of=as_of,
            limit=limit,
        )

    async def summary(
        self,
        symbol: str,
        *,
        as_of: datetime | None = None,
        limit: int = 20,
        cache: Any | None = None,
    ) -> Any:
        return await MarketAnalysisService(self.session, cache=cache).summarize(
            symbol,
            limit,
            as_of=as_of,
        )

    async def market_snapshot(
        self,
        symbol: str,
        limit: int = 20,
        *,
        as_of: datetime | None = None,
    ) -> Any:
        return await MarketEngine(self.session).calculate(
            symbol,
            limit,
            as_of=as_of,
        )

    async def technical(
        self,
        symbol: str,
        *,
        period: str = "1d",
        limit: int = 100,
        as_of: datetime | None = None,
        rsi_period: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        cycle_horizon: int = 5,
        cycle_service: CycleAnalysisService | None = None,
    ) -> Any:
        return await TechnicalEngine(
            self.session,
            cycle_service=cycle_service,
        ).calculate(
            symbol,
            period=period,
            limit=limit,
            as_of=as_of,
            rsi_period=rsi_period,
            macd_fast=macd_fast,
            macd_slow=macd_slow,
            macd_signal=macd_signal,
            cycle_horizon=cycle_horizon,
        )


class FinancialDataService:
    """统一 PIT 财务事实与盈利质量数据访问。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def fundamental(self, symbol: str, as_of: datetime) -> Any:
        return await FundamentalEngine(self.session).calculate(symbol, as_of)

    async def quality(self, symbol: str, as_of: datetime) -> Any:
        return await QualityEngine(self.session).calculate(symbol, as_of)


class ValuationService:
    """统一估值与情景目标价数据访问。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def valuation(
        self,
        symbol: str,
        as_of: datetime,
        *,
        price: Decimal | None = None,
        earnings_growth: Decimal | None = None,
        discount_rate: Decimal = Decimal("0.10"),
        growth_rate: Decimal = Decimal("0.03"),
    ) -> Any:
        return await ValuationEngine(self.session).calculate(
            symbol,
            as_of,
            price=price,
            earnings_growth=earnings_growth,
            discount_rate=discount_rate,
            growth_rate=growth_rate,
        )

    async def scenario(
        self,
        symbol: str,
        as_of: datetime,
        scenarios: list[ScenarioAssumption],
        *,
        price: Decimal | None = None,
    ) -> Any:
        return await ScenarioEngine(self.session).calculate(
            symbol,
            as_of,
            scenarios,
            price=price,
        )


class RiskService:
    """统一风险分析数据访问。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def calculate(
        self,
        symbol: str,
        as_of: datetime,
        *,
        period: str = "1d",
        limit: int = 252,
    ) -> Any:
        return await RiskEngine(self.session).calculate(
            symbol,
            as_of,
            period=period,
            limit=limit,
        )


class SupplyChainDataService:
    """统一供应链合同、订单和图谱数据访问。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def contracts(self, *, tenant_id: uuid.UUID | None = None) -> list[Any]:
        return await SupplyChainStore(self.session).list_contracts(
            tenant_id=tenant_id
        )

    def graph(self) -> GraphData:
        settings = get_settings()
        publisher = Neo4jPublisher(
            settings.neo4j_uri,
            settings.neo4j_user,
            settings.neo4j_password,
        )
        try:
            return publisher.list_graph()
        finally:
            publisher.close()


class DocumentRetrievalService:
    """统一文档块和证据读取，未来作为 RAG 检索的统一入口。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def blocks(
        self,
        *,
        document_version_id: uuid.UUID | None = None,
    ) -> list[Any]:
        return await NormalizedBlockStore(self.session).list_blocks(
            document_version_id=document_version_id
        )

    async def evidence_by_document(
        self,
        document_id: uuid.UUID,
        *,
        tenant_id: uuid.UUID,
    ) -> list[Any]:
        return await EvidenceClaimDraftStore(self.session).list_evidence_by_document(
            document_id,
            tenant_id=tenant_id,
        )
