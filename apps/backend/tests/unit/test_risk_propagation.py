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
