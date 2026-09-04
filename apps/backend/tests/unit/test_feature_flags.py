from datetime import datetime, timezone

from stock_research.core.feature_flags import FeatureFlagConfig, FeatureFlagService


def test_feature_flag_service_defaults_disabled() -> None:
    service = FeatureFlagService()

    assert service.is_enabled("canary") is False


def test_feature_flag_service_can_enable() -> None:
    service = FeatureFlagService({"canary": True})

    assert service.is_enabled("canary") is True
    assert len(service.list_flags()) == 1


def test_percentage_rollout_is_deterministic() -> None:
    service = FeatureFlagService(
        configs={"canary": FeatureFlagConfig(key="canary", percentage=50)}
    )

    first = service.is_enabled("canary", user_id="user-1")
    second = service.is_enabled("canary", user_id="user-1")
    assert first is second

    hits = sum(
        service.is_enabled("canary", user_id=f"user-{i}") for i in range(1000)
    )
    # Loose bounds to stay robust across hash inputs.
    assert 350 <= hits <= 650


def test_user_allowlist_overrides_percentage() -> None:
    service = FeatureFlagService(
        configs={
            "canary": FeatureFlagConfig(
                key="canary",
                percentage=0,
                user_allowlist=frozenset({"vip"}),
            )
        }
    )

    assert service.is_enabled("canary", user_id="vip") is True
    assert service.is_enabled("canary", user_id="normal") is False


def test_tenant_allowlist_overrides_percentage() -> None:
    service = FeatureFlagService(
        configs={
            "canary": FeatureFlagConfig(
                key="canary",
                percentage=0,
                tenant_allowlist=frozenset({"tenant-1"}),
            )
        }
    )

    assert service.is_enabled("canary", tenant_id="tenant-1") is True
    assert service.is_enabled("canary", tenant_id="tenant-2") is False


def test_kill_switch_rolls_back_everything() -> None:
    service = FeatureFlagService(
        configs={
            "canary": FeatureFlagConfig(
                key="canary",
                enabled=True,
                user_allowlist=frozenset({"vip"}),
                kill_switch=True,
            )
        }
    )

    assert service.is_enabled("canary", user_id="vip") is False


def test_time_window_gates_rollout() -> None:
    service = FeatureFlagService(
        configs={
            "canary": FeatureFlagConfig(
                key="canary",
                percentage=100,
                start_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                end_at=datetime(2026, 1, 31, tzinfo=timezone.utc),
            )
        }
    )

    assert service.is_enabled(
        "canary", user_id="u", now=datetime(2026, 1, 15, tzinfo=timezone.utc)
    ) is True
    assert service.is_enabled(
        "canary", user_id="u", now=datetime(2025, 12, 31, tzinfo=timezone.utc)
    ) is False
    assert service.is_enabled(
        "canary", user_id="u", now=datetime(2026, 2, 1, tzinfo=timezone.utc)
    ) is False


def test_percentage_zero_is_effective_rollback() -> None:
    service = FeatureFlagService(
        configs={"canary": FeatureFlagConfig(key="canary", percentage=0)}
    )

    assert service.is_enabled("canary", user_id="any-user") is False
