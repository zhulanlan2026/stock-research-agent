from stock_research.observability.prometheus import PrometheusRegistry


def test_prometheus_registry_renders_counter_and_gauge() -> None:
    registry = PrometheusRegistry()
    registry.inc_counter("requests_total")
    registry.inc_counter("requests_total")
    registry.set_gauge("inbox_pending", 3)

    rendered = registry.render()

    assert "requests_total 2.0" in rendered
    assert "inbox_pending 3" in rendered


def test_prometheus_registry_renders_empty() -> None:
    assert PrometheusRegistry().render() == ""
