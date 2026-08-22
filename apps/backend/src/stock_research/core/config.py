from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    jwt_secret_key: str = "dev-only-change-me-dev-only-change-me-1234567890"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "stock-research"
    jwt_audience: str = "stock-research-web"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 14
    refresh_cookie_name: str = "refresh_token"
    refresh_cookie_secure: bool = False

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
