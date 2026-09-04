from stock_research.model_gateway.discovery import ModelDescriptor, ModelDiscoveryService


class _FakeDecider:
    def __init__(self, enabled: dict[str, bool]) -> None:
        self._enabled = enabled

    async def is_enabled(
        self,
        key: str,
        *,
        environment: str = "production",
        tenant_id: str | None = None,
        user_id: str | None = None,
        now: object = None,
    ) -> bool:
        return self._enabled.get(key, False)


async def test_model_discovery_resolves_highest_priority() -> None:
    service = ModelDiscoveryService()
    service.register(ModelDescriptor("research", "model-a", frozenset({"reasoning"}), 1))
    service.register(ModelDescriptor("research", "model-b", frozenset({"reasoning"}), 2))

    assert await service.resolve("research", "reasoning") == "model-b"


async def test_model_discovery_returns_none_for_missing_capability() -> None:
    service = ModelDiscoveryService()
    service.register(ModelDescriptor("fast", "model-fast", frozenset({"chat"}), 1))

    assert await service.resolve("fast", "vision") is None


async def test_rollout_switches_model_alias() -> None:
    service = ModelDiscoveryService()
    service.register(ModelDescriptor("research", "model-stable", frozenset({"reasoning"}), 1))
    service.register(
        ModelDescriptor(
            "research",
            "model-canary",
            frozenset({"reasoning"}),
            2,
            rollout_key="research.canary",
        )
    )

    decider = _FakeDecider({"research.canary": True})
    assert (
        await service.resolve("research", "reasoning", decider=decider, user_id="u1")
        == "model-canary"
    )


async def test_rollout_falls_back_when_flag_off() -> None:
    service = ModelDiscoveryService()
    service.register(ModelDescriptor("research", "model-stable", frozenset({"reasoning"}), 1))
    service.register(
        ModelDescriptor(
            "research",
            "model-canary",
            frozenset({"reasoning"}),
            2,
            rollout_key="research.canary",
        )
    )

    decider = _FakeDecider({"research.canary": False})
    assert (
        await service.resolve("research", "reasoning", decider=decider, user_id="u1")
        == "model-stable"
    )


async def test_rollout_candidate_skipped_without_decider() -> None:
    service = ModelDiscoveryService()
    service.register(ModelDescriptor("research", "model-stable", frozenset({"reasoning"}), 1))
    service.register(
        ModelDescriptor(
            "research",
            "model-canary",
            frozenset({"reasoning"}),
            2,
            rollout_key="research.canary",
        )
    )

    assert await service.resolve("research", "reasoning") == "model-stable"
