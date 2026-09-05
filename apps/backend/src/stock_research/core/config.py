from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET_KEY = "dev-only-change-me-dev-only-change-me-1234567890"
DEV_COLLECTOR_INGEST_TOKEN = "dev-collector-token-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_name: str = "stock-research-platform"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://research:research123@localhost:5432/research_db"
    redis_url: str = "redis://:redis123@localhost:6379/0"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_secure: bool = False

    embedding_base_url: str = "https://api.siliconflow.cn/v1"
    embedding_api_key: str = ""
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024

    collector_ingest_token: str = DEV_COLLECTOR_INGEST_TOKEN
    jwt_secret_key: str = DEV_JWT_SECRET_KEY
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "stock-research"
    jwt_audience: str = "stock-research-web"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 14
    refresh_cookie_name: str = "refresh_token"
    refresh_cookie_secure: bool = False
    market_consume_interval_seconds: float = 1.0

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        if self.app_env != "production":
            if not self.jwt_secret_key:
                self.jwt_secret_key = DEV_JWT_SECRET_KEY
            if not self.collector_ingest_token:
                self.collector_ingest_token = DEV_COLLECTOR_INGEST_TOKEN
            return self

        if not self.refresh_cookie_secure:
            raise ValueError("REFRESH_COOKIE_SECURE must be true when APP_ENV=production")
        if self.jwt_secret_key == DEV_JWT_SECRET_KEY or len(self.jwt_secret_key) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be injected with a non-development value "
                "of at least 32 characters when APP_ENV=production"
            )
        if (
            self.collector_ingest_token == DEV_COLLECTOR_INGEST_TOKEN
            or len(self.collector_ingest_token) < 32
        ):
            raise ValueError(
                "COLLECTOR_INGEST_TOKEN must be injected with a non-development value "
                "of at least 32 characters when APP_ENV=production"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
