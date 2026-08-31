from stock_research.observability.otel import OtelConfigurator


def test_otel_configurator_does_not_raise() -> None:
    configurator = OtelConfigurator("stock-research-backend")

    assert isinstance(configurator.configure(), bool)
