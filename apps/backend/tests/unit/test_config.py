import pytest
from pydantic import ValidationError

from stock_research.core.config import DEV_COLLECTOR_INGEST_TOKEN, DEV_JWT_SECRET_KEY, Settings


def test_development_defaults_are_allowed() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.app_env == "development"
    assert settings.refresh_cookie_secure is False


def test_development_empty_jwt_secret_falls_back_to_dev_default() -> None:
    settings = Settings(jwt_secret_key="", _env_file=None)  # type: ignore[call-arg]
    assert settings.jwt_secret_key == DEV_JWT_SECRET_KEY


def test_development_empty_collector_ingest_token_falls_back_to_dev_default() -> None:
    settings = Settings(collector_ingest_token="", _env_file=None)  # type: ignore[call-arg]
    assert settings.collector_ingest_token == DEV_COLLECTOR_INGEST_TOKEN


def test_production_requires_secure_refresh_cookie() -> None:
    with pytest.raises(ValidationError):
        Settings(  # type: ignore[call-arg]
            app_env="production",
            refresh_cookie_secure=False,
            jwt_secret_key="p" * 32,
            _env_file=None,
        )


def test_production_requires_injected_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(  # type: ignore[call-arg]
            app_env="production",
            refresh_cookie_secure=True,
            jwt_secret_key=DEV_JWT_SECRET_KEY,
            collector_ingest_token="c" * 32,
            _env_file=None,
        )


def test_production_requires_injected_collector_ingest_token() -> None:
    with pytest.raises(ValidationError):
        Settings(  # type: ignore[call-arg]
            app_env="production",
            refresh_cookie_secure=True,
            jwt_secret_key="p" * 32,
            collector_ingest_token=DEV_COLLECTOR_INGEST_TOKEN,
            _env_file=None,
        )


def test_production_valid_configuration_is_accepted() -> None:
    settings = Settings(  # type: ignore[call-arg]
        app_env="production",
        refresh_cookie_secure=True,
        jwt_secret_key="p" * 32,
        collector_ingest_token="c" * 32,
        _env_file=None,
    )
    assert settings.refresh_cookie_secure is True
    assert settings.collector_ingest_token == "c" * 32
