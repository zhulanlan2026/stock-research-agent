from stock_research.entitlements.policy import can_consume_quota, plan_has_feature, quota_available


def test_plan_features() -> None:
    assert plan_has_feature("paid", "standard_research")
    assert not plan_has_feature("free", "report_export")


def test_quota_available() -> None:
    assert quota_available(100, 30, 20) == 50
    assert quota_available(100, 80, 30) == 0


def test_can_consume_quota() -> None:
    assert can_consume_quota(10, 8, 1, amount=1)
    assert not can_consume_quota(10, 8, 2, amount=1)
    assert not can_consume_quota(10, 8, 1, amount=0)
