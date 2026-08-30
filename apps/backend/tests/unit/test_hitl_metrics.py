from stock_research.review.metrics import HitlMetricsService


def test_hitl_metrics_calculates_rates() -> None:
    metrics = HitlMetricsService().calculate(
        ["APPROVED", "APPROVED", "NEEDS_REVISION", "REJECTED"]
    )

    assert metrics.total == 4
    assert metrics.approved == 2
    assert metrics.approval_rate == 0.5


def test_hitl_metrics_handles_empty() -> None:
    metrics = HitlMetricsService().calculate([])

    assert metrics.total == 0
    assert metrics.approval_rate == 0.0
