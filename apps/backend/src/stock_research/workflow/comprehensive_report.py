from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from stock_research.agents.engine_agents import build_research_agents
from stock_research.agents.orchestrator import AgentOrchestrator
from stock_research.agents.protocol import AgentContext
from stock_research.agents.registry import AgentRegistry
from stock_research.core.config import get_settings
from stock_research.documents.draft import EvidenceClaimDraftStore
from stock_research.fundamental.professional import (
    ProfessionalFinancialEngine,
    professional_payload,
)
from stock_research.market.cycle import CycleAnalysisService
from stock_research.market.torch_lstm import TorchLstmCyclePredictor
from stock_research.model_gateway.deepseek import DeepSeekClient
from stock_research.model_gateway.gateway import ModelGateway
from stock_research.services.evidence_strength import EvidenceStrengthService
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
        effective_as_of = as_of or datetime.now(timezone.utc)
        context = AgentContext(
            task_id="comprehensive-report",
            symbol=symbol,
            mode=mode,
            as_of=effective_as_of,
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

        evidence_data = await self._evidence_strength(
            factory=session_factory,
            symbol=symbol,
            as_of=effective_as_of,
            tenant_id=tenant_id,
        )
        professional_data = await self._professional_financial(
            factory=session_factory,
            symbol=symbol,
            as_of=effective_as_of,
        )

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
            ]
            + [
                ReportSectionResponse(
                    title="专业财务",
                    data=professional_data,
                ),
                ReportSectionResponse(
                    title="证据强度",
                    data=evidence_data,
                )
            ],
        )

    async def _evidence_strength(
        self,
        *,
        factory: Any,
        symbol: str,
        as_of: datetime,
        tenant_id: str | None,
    ) -> dict[str, Any]:
        try:
            tenant_uuid = uuid.UUID(tenant_id) if tenant_id else None
        except ValueError:
            tenant_uuid = None

        evidence: list[Any] = []
        if tenant_uuid is not None:
            async with factory() as session:
                evidence = await EvidenceClaimDraftStore(session).list_evidence_by_symbol(
                    symbol,
                    tenant_id=tenant_uuid,
                    as_of=as_of,
                )

        return EvidenceStrengthService().summarize(
            symbol=symbol,
            as_of=as_of,
            evidence=evidence,
        )

    async def _professional_financial(
        self,
        *,
        factory: Any,
        symbol: str,
        as_of: datetime,
    ) -> dict[str, Any]:
        async with factory() as session:
            snapshot = await ProfessionalFinancialEngine(session).calculate(
                symbol,
                as_of,
            )
        return professional_payload(snapshot)

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
