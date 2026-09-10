from stock_research.outbox.handlers import build_default_registry


def test_default_registry_has_research_approved_handler() -> None:
    registry = build_default_registry()

    assert registry.get("research.approved") is not None
