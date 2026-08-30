from stock_research.model_gateway.discovery import ModelDescriptor, ModelDiscoveryService


def test_model_discovery_resolves_highest_priority() -> None:
    service = ModelDiscoveryService()
    service.register(ModelDescriptor("research", "model-a", frozenset({"reasoning"}), 1))
    service.register(ModelDescriptor("research", "model-b", frozenset({"reasoning"}), 2))

    assert service.resolve("research", "reasoning") == "model-b"


def test_model_discovery_returns_none_for_missing_capability() -> None:
    service = ModelDiscoveryService()
    service.register(ModelDescriptor("fast", "model-fast", frozenset({"chat"}), 1))

    assert service.resolve("fast", "vision") is None
