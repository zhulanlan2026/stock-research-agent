from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class FactorIC:
    factor: str
    observations: int
    ic_mean: Decimal | None
    ic_std: Decimal | None
    icir: Decimal | None
    ic_positive_ratio: Decimal | None


def _rank(values: list[Decimal]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(indexed):
        j = index
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[index][1]:
            j += 1
        average_rank = (index + j) / 2 + 1
        for k in range(index, j + 1):
            ranks[indexed[k][0]] = average_rank
        index = j + 1
    return ranks


def spearman(x: list[Decimal], y: list[Decimal]) -> Decimal | None:
    if len(x) != len(y) or len(x) < 3:
        return None
    x_rank = _rank(x)
    y_rank = _rank(y)
    n = len(x)
    x_mean = sum(x_rank) / n
    y_mean = sum(y_rank) / n
    numerator = sum((x_rank[i] - x_mean) * (y_rank[i] - y_mean) for i in range(n))
    x_var = sum((value - x_mean) ** 2 for value in x_rank)
    y_var = sum((value - y_mean) ** 2 for value in y_rank)
    denominator = (x_var * y_var) ** 0.5
    if denominator == 0:
        return None
    return Decimal(str(numerator / denominator))


def summarize_ic(factor: str, values: list[Decimal]) -> FactorIC | None:
    """把一条 IC 序列汇总为均值、标准差、ICIR 和正值占比。"""
    valid = [value for value in values if value is not None]
    if not valid:
        return None
    mean = sum(valid, Decimal("0")) / Decimal(len(valid))
    variance = sum(
        (value - mean) ** 2 for value in valid
    ) / Decimal(len(valid))
    std = variance.sqrt()
    icir = mean / std if std != 0 else None
    positive = sum(1 for value in valid if value > 0)
    positive_ratio = Decimal(positive) / Decimal(len(valid))
    return FactorIC(
        factor=factor,
        observations=len(valid),
        ic_mean=mean,
        ic_std=std,
        icir=icir,
        ic_positive_ratio=positive_ratio,
    )
