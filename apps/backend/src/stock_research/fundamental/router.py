from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.auth.dependencies import get_current_user
from stock_research.fundamental.engine import FundamentalEngine, FundamentalSnapshot
from stock_research.fundamental.schemas import (
    FundamentalAnalysisRequest,
    FundamentalAnalysisResponse,
)
from stock_research.stores.models.iam import User
from stock_research.stores.session import get_session

router = APIRouter(prefix="/fundamental", tags=["fundamental"])


@router.post("/analysis", response_model=FundamentalAnalysisResponse)
async def analyze_fundamental(
    body: FundamentalAnalysisRequest,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> FundamentalAnalysisResponse:
    snapshot = await FundamentalEngine(session).calculate(
        body.symbol,
        body.as_of or datetime.now(timezone.utc),
    )
    return FundamentalAnalysisResponse(
        symbol=snapshot.symbol,
        as_of=snapshot.as_of,
        coverage=float(snapshot.coverage),
        summary=_summary(snapshot),
        metrics={
            "营收": _str(snapshot.metrics["revenue"]),
            "净利润": _str(snapshot.metrics["net_income"]),
            "总资产": _str(snapshot.metrics["total_assets"]),
            "总负债": _str(snapshot.metrics["total_liabilities"]),
            "总权益": _str(snapshot.metrics["total_equity"]),
        },
        ratios={
            "毛利率": _str(snapshot.ratios["gross_margin"]),
            "净利率": _str(snapshot.ratios["net_margin"]),
            "ROE": _str(snapshot.ratios["roe"]),
            "ROA": _str(snapshot.ratios["roa"]),
            "负债权益比": _str(snapshot.ratios["debt_to_equity"]),
            "流动比率": _str(snapshot.ratios["current_ratio"]),
            "现金流/净利润": _str(
                snapshot.ratios["operating_cash_flow_to_net_income"]
            ),
        },
    )


def _summary(snapshot: FundamentalSnapshot) -> str:
    net_income = snapshot.metrics["net_income"]
    net_margin = snapshot.ratios["net_margin"]
    roe = snapshot.ratios["roe"]
    parts: list[str] = []
    if net_income is not None:
        parts.append(f"净利润 {net_income} 元")
    if net_margin is not None:
        parts.append(f"净利率 {net_margin:.2%}")
    if roe is not None:
        parts.append(f"ROE {roe:.2%}")
    if not parts:
        return f"{snapshot.symbol} 暂无足够财务数据。"
    return f"{snapshot.symbol} 财务概况：" + "，".join(parts) + "。"


def _str(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None
