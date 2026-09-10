from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from stock_research.agents.protocol import (
    AgentContext,
    AgentManifest,
    AgentResult,
)
from stock_research.agents.react_skills import ResearchContextSkill
from stock_research.agents.report_pipeline import (
    StructuredReportAgent,
    StructuredReviewAgent,
)
from stock_research.agents.research_summary import ResearchSummaryAgent
from stock_research.agents.supplementary_agents import NewsAgent, SupplyChainAgent
from stock_research.fundamental.engine import FundamentalEngine
from stock_research.fundamental.risk import RiskEngine
from stock_research.market.cycle import CycleAnalysisService
from stock_research.market.engine import MarketEngine, TechnicalEngine
from stock_research.skills.gateway import SkillGateway


class FundamentalEngineAgent:
    """将确定性 FundamentalEngine 包装为可并行调度的 Agent。"""

    _manifest = AgentManifest(
        name="fundamental",
        version="fundamental:1.0.0",
        description="PIT 财务事实确定性基本面快照",
        execution_type="deterministic_engine",
        required_scopes=frozenset({"stock.fundamental.read"}),
        allowed_skills=frozenset(),
        external_model_allowed=False,
        side_effect="NONE",
    )

    def __init__(
        self,
        engine: FundamentalEngine | None = None,
        *,
        session_factory: Any | None = None,
    ) -> None:
        if engine is None and session_factory is None:
            raise ValueError("engine or session_factory is required")
        self._engine = engine
        self._session_factory = session_factory

    @property
    def manifest(self) -> AgentManifest:
        return self._manifest

    async def run(self, context: AgentContext) -> AgentResult:
        as_of = context.as_of or datetime.now(timezone.utc)
        if self._engine is not None:
            snapshot = await self._engine.calculate(context.symbol, as_of)
        else:
            session_factory = self._session_factory
            if session_factory is None:
                raise RuntimeError("session_factory is not configured")
            async with session_factory() as session:
                snapshot = await FundamentalEngine(session).calculate(
                    context.symbol,
                    as_of,
                )
        return AgentResult(
            agent=self.manifest.name,
            status="COMPLETED",
            data={"result": snapshot},
            module_versions={"fundamental": snapshot.module_version},
        )


class TechnicalEngineAgent:
    """将确定性 TechnicalEngine 包装为可并行调度的 Agent。"""

    _manifest = AgentManifest(
        name="technical",
        version="technical:1.1.0",
        description="K 线技术指标确定性计算",
        execution_type="deterministic_engine",
        required_scopes=frozenset({"stock.technical.read"}),
        allowed_skills=frozenset({"skill.technical.execute"}),
        external_model_allowed=False,
        side_effect="NONE",
    )

    def __init__(
        self,
        engine: TechnicalEngine | None = None,
        *,
        session_factory: Any | None = None,
        cycle_service: CycleAnalysisService | None = None,
    ) -> None:
        if engine is None and session_factory is None:
            raise ValueError("engine or session_factory is required")
        self._engine = engine
        self._session_factory = session_factory
        self._cycle_service = cycle_service

    @property
    def manifest(self) -> AgentManifest:
        return self._manifest

    async def run(self, context: AgentContext) -> AgentResult:
        period = _string_setting(context.state, "technical_period", "1d")
        limit = _int_setting(context.state, "technical_limit", 100)
        rsi_period = _int_setting(context.state, "rsi_period", 14)
        macd_fast = _int_setting(context.state, "macd_fast", 12)
        macd_slow = _int_setting(context.state, "macd_slow", 26)
        macd_signal = _int_setting(context.state, "macd_signal", 9)
        cycle_horizon = _int_setting(context.state, "technical_cycle_horizon", 5)
        if self._engine is not None:
            result = await self._engine.calculate(
                context.symbol,
                period=period,
                limit=limit,
                rsi_period=rsi_period,
                macd_fast=macd_fast,
                macd_slow=macd_slow,
                macd_signal=macd_signal,
                cycle_horizon=cycle_horizon,
            )
        else:
            session_factory = self._session_factory
            if session_factory is None:
                raise RuntimeError("session_factory is not configured")
            async with session_factory() as session:
                result = await TechnicalEngine(
                    session,
                    cycle_service=self._cycle_service,
                ).calculate(
                    context.symbol,
                    period=period,
                    limit=limit,
                    rsi_period=rsi_period,
                    macd_fast=macd_fast,
                    macd_slow=macd_slow,
                    macd_signal=macd_signal,
                    cycle_horizon=cycle_horizon,
                )
        return AgentResult(
            agent=self.manifest.name,
            status="COMPLETED",
            data={"result": result},
            module_versions={"technical": result.module_version},
        )


class MarketEngineAgent:
    """将确定性 MarketEngine 包装为可并行调度的 Agent。"""

    _manifest = AgentManifest(
        name="market",
        version="market:1.0.0",
        description="实时行情确定性摘要",
        execution_type="deterministic_engine",
        required_scopes=frozenset({"stock.market.read"}),
        allowed_skills=frozenset({"skill.market.execute"}),
        external_model_allowed=False,
        side_effect="NONE",
    )

    def __init__(
        self,
        engine: MarketEngine | None = None,
        *,
        session_factory: Any | None = None,
    ) -> None:
        if engine is None and session_factory is None:
            raise ValueError("engine or session_factory is required")
        self._engine = engine
        self._session_factory = session_factory

    @property
    def manifest(self) -> AgentManifest:
        return self._manifest

    async def run(self, context: AgentContext) -> AgentResult:
        limit = _int_setting(context.state, "market_limit", 20)
        if self._engine is not None:
            result = await self._engine.calculate(context.symbol, limit=limit)
        else:
            session_factory = self._session_factory
            if session_factory is None:
                raise RuntimeError("session_factory is not configured")
            async with session_factory() as session:
                result = await MarketEngine(session).calculate(
                    context.symbol,
                    limit=limit,
                )
        return AgentResult(
            agent=self.manifest.name,
            status="COMPLETED",
            data={"result": result},
            module_versions={"market": result.module_version},
        )


class RiskEngineAgent:
    """将确定性 RiskEngine 包装为依赖核心模块完成后执行的 Agent。"""

    _manifest = AgentManifest(
        name="risk",
        version="risk:1.0.0",
        description="财务风险、市场波动与回撤确定性风险快照",
        execution_type="deterministic_engine",
        required_scopes=frozenset({"stock.risk.read"}),
        allowed_skills=frozenset(),
        external_model_allowed=False,
        side_effect="NONE",
        dependencies=("fundamental", "technical", "market"),
    )

    def __init__(
        self,
        engine: RiskEngine | None = None,
        *,
        session_factory: Any | None = None,
    ) -> None:
        if engine is None and session_factory is None:
            raise ValueError("engine or session_factory is required")
        self._engine = engine
        self._session_factory = session_factory

    @property
    def manifest(self) -> AgentManifest:
        return self._manifest

    async def run(self, context: AgentContext) -> AgentResult:
        as_of = context.as_of or datetime.now(timezone.utc)
        period = _string_setting(context.state, "risk_period", "1d")
        limit = _int_setting(context.state, "risk_limit", 252)
        if self._engine is not None:
            result = await self._engine.calculate(
                context.symbol,
                as_of,
                period=period,
                limit=limit,
            )
        else:
            session_factory = self._session_factory
            if session_factory is None:
                raise RuntimeError("session_factory is not configured")
            async with session_factory() as session:
                result = await RiskEngine(session).calculate(
                    context.symbol,
                    as_of,
                    period=period,
                    limit=limit,
                )
        return AgentResult(
            agent=self.manifest.name,
            status="COMPLETED",
            data={"result": result},
            module_versions={"risk": result.module_version},
        )


def build_core_agents(
    session_factory: Any,
    *,
    cycle_service: CycleAnalysisService | None = None,
) -> list[Any]:
    return [
        FundamentalEngineAgent(session_factory=session_factory),
        TechnicalEngineAgent(
            session_factory=session_factory,
            cycle_service=cycle_service,
        ),
        MarketEngineAgent(session_factory=session_factory),
    ]


def build_research_agents(
    session_factory: Any,
    model_gateway: Any | None = None,
    *,
    model_alias: str = "research",
    react_observer: Any | None = None,
    cycle_service: CycleAnalysisService | None = None,
) -> list[Any]:
    skill_gateway = SkillGateway()
    skill_gateway.register_skill(
        ResearchContextSkill.manifest,
        ResearchContextSkill().execute,
    )
    return [
        *build_core_agents(
            session_factory,
            cycle_service=cycle_service,
        ),
        NewsAgent(session_factory=session_factory),
        SupplyChainAgent(),
        RiskEngineAgent(session_factory=session_factory),
        ResearchSummaryAgent(
            model_gateway=model_gateway,
            skill_gateway=skill_gateway,
            observer=react_observer,
            model_alias=model_alias,
        ),
        StructuredReportAgent(
            model_gateway=model_gateway,
            skill_gateway=skill_gateway,
            observer=react_observer,
            model_alias=model_alias,
        ),
        StructuredReviewAgent(
            model_gateway=model_gateway,
            skill_gateway=skill_gateway,
            observer=react_observer,
            model_alias=model_alias,
        ),
    ]


def _string_setting(state: Any, key: str, default: str) -> str:
    value = state.get(key)
    return str(value) if value is not None else default


def _int_setting(state: Any, key: str, default: int) -> int:
    value = state.get(key)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
