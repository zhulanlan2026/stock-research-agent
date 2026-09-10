from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SUPPORTED_PERIODS = frozenset({"1m", "5m", "15m", "30m", "1h", "1d"})
SUPPORTED_NEWS_KINDS = frozenset({"news", "announcement"})


class CollectorSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="COLLECTOR_",
        extra="ignore",
    )

    app_env: str = "development"
    backend_url: str = "http://localhost:8000/api/v1"
    ingest_token: str = "dev-collector-token-change-me"
    # 需要订阅实时行情的合约代码，逗号分隔，例如 600519.SH,000001.SZ。
    collect_symbols: str = ""
    # 需要下载历史 K 线的周期，逗号分隔，例如 1m,5m,1d。
    collect_periods: str = "1m,1d"
    # 是否采集 XTQuant 公告/新闻。公告 provider 已接入；news 类型字段未确认前建议只开 announcement。
    collect_news_enabled: bool = False
    # 新闻/公告类型，逗号分隔，可选 news,announcement。
    collect_news_kinds: str = "announcement"
    # 采集器本地持久化缓冲，仅用于行情采集，不替代 PostgreSQL 业务真相源。
    wal_path: str = "./data/collector-local-wal.sqlite"
    poll_interval_seconds: float = 1.0
    log_level: str = "INFO"

    @property
    def symbol_list(self) -> list[str]:
        return [symbol.strip() for symbol in self.collect_symbols.split(",") if symbol.strip()]

    @property
    def period_list(self) -> list[str]:
        return [period.strip() for period in self.collect_periods.split(",") if period.strip()]

    @property
    def news_kind_list(self) -> list[str]:
        return [kind.strip() for kind in self.collect_news_kinds.split(",") if kind.strip()]

    @model_validator(mode="after")
    def _validate_periods(self) -> "CollectorSettings":
        invalid = [period for period in self.period_list if period not in SUPPORTED_PERIODS]
        if invalid:
            raise ValueError(
                f"unsupported COLLECTOR_COLLECT_PERIODS: {', '.join(invalid)}"
            )
        invalid_news = [
            kind for kind in self.news_kind_list if kind not in SUPPORTED_NEWS_KINDS
        ]
        if invalid_news:
            raise ValueError(
                f"unsupported COLLECTOR_COLLECT_NEWS_KINDS: {', '.join(invalid_news)}"
            )
        return self


@lru_cache
def get_settings() -> CollectorSettings:
    return CollectorSettings()
