from stock_research.core.feature_flags import FeatureFlagService


def test_feature_flag_service_defaults_disabled() -> None:
    service = FeatureFlagService()

    assert service.is_enabled("canary") is False


def test_feature_flag_service_can_enable() -> None:
    service = FeatureFlagService({"canary": True})

    assert service.is_enabled("canary") is True
    assert len(service.list_flags()) == 1
