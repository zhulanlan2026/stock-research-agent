from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from stock_research.agents.protocol import AgentContext, AgentResult
from stock_research.agents.research_summary import ResearchSummaryAgent


async def test_research_summary_agent_consumes_module_results() -> None:
    results = {
        "fundamental": AgentResult(
            agent="fundamental",
            status="COMPLETED",
            data={
                "result": SimpleNamespace(
                    module_version="fundamental:1.0.0",
                    coverage=Decimal("0.75"),
                    metrics={
                        "revenue": Decimal("100"),
                        "net_income": Decimal("20"),
                    },
                    ratios={
                        "roe": Decimal("0.15"),
                        "net_margin": Decimal("0.20"),
                    },
                )
            },
        ),
        "technical": AgentResult(
            agent="technical",
            status="COMPLETED",
            data={
                "result": SimpleNamespace(
                    module_version="technical:1.0.0",
                    period="1d",
                    points=[
                        SimpleNamespace(
                            time=datetime(2026, 4, 1, tzinfo=timezone.utc),
                            rsi=55.5,
                            macd_dif=0.2,
                            macd_dea=0.1,
                            macd_hist=0.2,
                        )
                    ],
                )
            },
        ),
        "market": AgentResult(
            agent="market",
            status="COMPLETED",
            data={
                "result": SimpleNamespace(
                    module_version="market:1.0.0",
                    summary=SimpleNamespace(
                        last_price=10.5,
                        change_pct=5.0,
                        sample_count=3,
                    ),
                )
            },
        ),
        "supply_chain": AgentResult(
            agent="supply_chain",
            status="COMPLETED",
            data={
                "result": SimpleNamespace(
                    module_version="supply_chain:1.0.0",
                    nodes=("公司A", "公司B"),
                    edges=(
                        {
                            "source": "公司A",
                            "predicate": "signed_contract_with",
                            "target": "公司B",
                        },
                    ),
                )
            },
        ),
        "news": AgentResult(
            agent="news",
            status="COMPLETED",
            data={
                "result": SimpleNamespace(
                    module_version="news:1.0.0",
                    query="测试新闻",
                    items=(),
                )
            },
        ),
        "risk": AgentResult(
            agent="risk",
            status="COMPLETED",
            data={
                "result": SimpleNamespace(
                    module_version="risk:1.0.0",
                    risk_level="MEDIUM",
                    risk_action="RESTRICT",
                    risk_score=Decimal("0.4"),
                    coverage=Decimal("1"),
                    market_risk={
                        "annualized_volatility": Decimal("0.3"),
                        "max_drawdown": Decimal("0.2"),
                    },
                )
            },
        ),
    }
    agent = ResearchSummaryAgent()

    result = await agent.run(
        AgentContext(
            task_id="task-1",
            symbol="600519.SH",
            mode="standard",
            as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
            state={"results": results},
        )
    )

    summary = result.data["result"]
    assert summary.module_summaries["risk"]["risk_level"] == "MEDIUM"
    assert summary.coverage == 1.0
    assert "600519.SH" in summary.summary_text
