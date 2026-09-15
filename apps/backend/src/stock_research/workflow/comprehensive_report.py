from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from stock_research.agents.engine_agents import build_research_agents
from stock_research.agents.orchestrator import AgentOrchestrator
from stock_research.agents.protocol import AgentContext
from stock_research.agents.registry import AgentRegistry
from stock_research.core.config import get_settings
from stock_research.market.cycle import CycleAnalysisService
from stock_research.market.torch_lstm import TorchLstmCyclePredictor
from stock_research.model_gateway.deepseek import DeepSeekClient
from stock_research.model_gateway.gateway import ModelGateway
from stock_research.workflow.schemas import (
    ComprehensiveReportResponse,
    ReportSectionResponse,
)


class ComprehensiveReportService:
    """同步执行完整研究 Agent DAG 并返回综合报告。"""

    async def generate(
        self,
        session_factory: Any,
        *,
        symbol: str,
        mode: str,
        as_of: datetime | None = None,
        modules: list[str] | None = None,
        tenant_id: str | None = None,
        user_id: str | None = None,
    ) -> ComprehensiveReportResponse:
        settings = get_settings()
        model_gateway = self._build_model_gateway(settings)
        cycle_service = self._build_cycle_service(settings)
        requested = ("report",)

        registry = AgentRegistry(
            build_research_agents(
                session_factory,
                model_gateway,
                model_alias=settings.llm_model,
                cycle_service=cycle_service,
            )
        )
        orchestrator = AgentOrchestrator(registry, prefer_langgraph=True)
        context = AgentContext(
            task_id="comprehensive-report",
            symbol=symbol,
            mode=mode,
            as_of=as_of or datetime.now(timezone.utc),
            tenant_id=tenant_id,
            user_id=user_id,
            scopes=frozenset({"research.standard.execute"}),
            state={
                "technical_period": "1d",
                "technical_cycle_horizon": settings.technical_cycle_horizon,
                "market_limit": 20,
                "news_limit": 20,
                "risk_period": "1d",
                "risk_limit": 252,
            },
        )

        result = await orchestrator.run(context, requested)
        report_agent = result.results.get("report")
        if report_agent is None or report_agent.status != "COMPLETED":
            raise RuntimeError("comprehensive report agent did not complete")

        report = report_agent.data.get("result")
        if report is None:
            raise RuntimeError("comprehensive report result is missing")

        return ComprehensiveReportResponse(
            symbol=report.symbol,
            as_of=report.as_of,
            module_version=report.module_version,
            summary=report.summary,
            narrative=report.narrative,
            sections=[
                ReportSectionResponse(
                    title=section.title,
                    data=dict(section.data),
                )
                for section in report.sections
            ],
        )

    def _build_model_gateway(self, settings: Any) -> ModelGateway | None:
        if not settings.llm_api_key:
            return None
        client = DeepSeekClient(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
        )
        return ModelGateway(client)

    def _build_cycle_service(self, settings: Any) -> CycleAnalysisService:
        if not settings.technical_lstm_enabled:
            return CycleAnalysisService()
        predictor = TorchLstmCyclePredictor(
            seed=settings.technical_lstm_seed,
            hidden_size=settings.technical_lstm_hidden_size,
            epochs=settings.technical_lstm_epochs,
            window=settings.technical_lstm_window,
        )
        return CycleAnalysisService(lstm_predictor=predictor)
