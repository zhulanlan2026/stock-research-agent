from stock_research.supply_chain.risk_propagation import RiskPropagationService


def test_risk_propagation_propagates_along_edges() -> None:
    result = RiskPropagationService().propagate(
        edges=[("A", "supplies", "B")],
        initial_risk={"A": 1.0, "B": 0.0},
        damping=0.5,
    )

    assert result["B"] == 0.5


def test_risk_propagation_keeps_isolated_nodes_unchanged() -> None:
    result = RiskPropagationService().propagate(
        edges=[],
        initial_risk={"A": 0.8},
    )

    assert result == {"A": 0.8}


def test_risk_propagation_multiple_steps() -> None:
    result = RiskPropagationService().propagate(
        edges=[("A", "supplies", "B"), ("B", "supplies", "C")],
        initial_risk={"A": 1.0},
        damping=0.5,
        max_steps=2,
    )

    assert result["A"] == 1.0
    assert result["B"] == 0.75
    assert result["C"] == 0.25
