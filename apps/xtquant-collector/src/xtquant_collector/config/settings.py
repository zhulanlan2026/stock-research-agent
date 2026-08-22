from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class CollectorSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    backend_url: str = "http://localhost:8000/api/v1"
    wal_path: str = "./data/wal.sqlite"
    poll_interval_seconds: float = 1.0
    log_level: str = "INFO"


@lru_cache
def get_settings() -> CollectorSettings:
    return CollectorSettings()
