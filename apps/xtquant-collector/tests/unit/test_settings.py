from xtquant_collector.config.settings import CollectorSettings


def test_settings_defaults() -> None:
    settings = CollectorSettings(_env_file=None)  # type: ignore[call-arg]
    assert settings.backend_url == "http://localhost:8000/api/v1"
    assert settings.poll_interval_seconds == 1.0
    assert settings.log_level == "INFO"
