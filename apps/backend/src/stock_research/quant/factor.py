from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FactorDefinition:
    name: str
    category: str
    description: str
    source: str  # "fact" 表示直接读 financial_fact，其它由计算器生成


# 因子池目录：财务/估值/规模因子直接复用投研已入库的 financial.fact，
# 技术/动量因子由日线 K 线确定性计算。
FACTOR_POOL: tuple[FactorDefinition, ...] = (
    FactorDefinition("roe", "quality", "净资产收益率", "fact"),
    FactorDefinition("roa", "quality", "总资产收益率", "fact"),
    FactorDefinition("netprofit_margin", "quality", "净利率", "fact"),
    FactorDefinition("grossprofit_margin", "quality", "毛利率", "fact"),
    FactorDefinition("debt_to_assets", "quality", "资产负债率", "fact"),
    FactorDefinition("current_ratio", "quality", "流动比率", "fact"),
    FactorDefinition("pe_ttm", "valuation", "市盈率 TTM", "fact"),
    FactorDefinition("pb", "valuation", "市净率", "fact"),
    FactorDefinition("ps_ttm", "valuation", "市销率 TTM", "fact"),
    FactorDefinition("dv_ttm", "valuation", "股息率 TTM", "fact"),
    FactorDefinition("total_mv", "size", "总市值", "fact"),
    FactorDefinition("circ_mv", "size", "流通市值", "fact"),
    FactorDefinition("momentum_20", "momentum", "20 日动量", "computed"),
    FactorDefinition("momentum_60", "momentum", "60 日动量", "computed"),
    FactorDefinition("volatility_20", "risk", "20 日年化波动率", "computed"),
    FactorDefinition("rsi_14", "momentum", "14 日 RSI", "computed"),
)
