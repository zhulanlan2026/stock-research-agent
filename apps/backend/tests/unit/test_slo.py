from stock_research.observability.slo import SloEvaluator


def test_slo_evaluator_checks_latency_bounds() -> None:
    evaluator = SloEvaluator()

    assert evaluator.is_compliant("standard_retrieval_p95_s", 1.0) is True
    assert evaluator.is_compliant("standard_retrieval_p95_s", 2.0) is False


def test_slo_evaluator_checks_availability() -> None:
    evaluator = SloEvaluator()

    assert evaluator.is_compliant("availability", 0.9995) is True
    assert evaluator.is_compliant("availability", 0.99) is False


def test_slo_evaluator_enforces_zero_tolerance() -> None:
    evaluator = SloEvaluator()

    assert evaluator.is_compliant("cross_tenant_unauthorized_recall", 0) is True
    assert evaluator.is_compliant("cross_tenant_unauthorized_recall", 1) is False


def test_slo_evaluator_unknown_metric_is_compliant() -> None:
    assert SloEvaluator().is_compliant("unknown_metric", 999.0) is True


def test_slo_evaluator_all_compliant() -> None:
    observations = {
        "standard_retrieval_p95_s": 1.0,
        "cross_tenant_unauthorized_recall": 0,
        "duplicate_visible_side_effects": 0,
    }
    assert SloEvaluator().all_compliant(observations) is True

    observations["standard_retrieval_p95_s"] = 3.0
    assert SloEvaluator().all_compliant(observations) is False
