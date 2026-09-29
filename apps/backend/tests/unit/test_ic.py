from decimal import Decimal

from stock_research.quant.ic import spearman, summarize_ic


def test_spearman_perfect_positive() -> None:
    x = [Decimal(str(i)) for i in range(10)]
    y = [Decimal(str(i * 2)) for i in range(10)]

    assert spearman(x, y) == Decimal("1")


def test_spearman_perfect_negative() -> None:
    x = [Decimal(str(i)) for i in range(10)]
    y = [Decimal(str(10 - i)) for i in range(10)]

    assert spearman(x, y) == Decimal("-1")


def test_summarize_ic() -> None:
    summary = summarize_ic("factor", [Decimal("0.1"), Decimal("0.2"), Decimal("-0.1")])

    assert summary is not None
    assert summary.observations == 3
    assert summary.ic_positive_ratio == Decimal("2") / Decimal("3")
