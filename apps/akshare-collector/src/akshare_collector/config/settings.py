from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SUPPORTED_PERIODS = frozenset({"1m", "5m", "15m", "30m", "1h", "1d"})


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

    # 需要采集的 A 股代码，逗号分隔，例如 600519.SH,000001.SZ。
    collect_symbols: str = ""
    # 需要采集的 K 线周期，逗号分隔，例如 1m,5m,1d。
    collect_periods: str = "1m,1d"
    # 财务事实回补天数。
    history_days: int = 730
    # 日线 K 线回补天数。
    bars_history_days: int = 730

    # 行情主数据源：akshare 或 tushare。
    market_source: str = "akshare"
    # Tushare 复权类型：空=不复权，qfq=前复权，hfq=后复权（仅日线有效）。
    tushare_adjust: str = ""

    # 是否采集 AKShare 公告。
    collect_news_enabled: bool = False

    # 是否采集本地 JSON Lines 财务事实。
    collect_financial_enabled: bool = False
    # 财务事实数据源：jsonl（本地 JSON Lines）或 tushare。
    financial_source: str = "jsonl"
    financial_data_path: str = "./data/financial-facts.jsonl"

    # Tushare 交叉验证。token 为空时自动跳过。
    tushare_token: str = ""
    cross_validation_enabled: bool = True
    cross_validation_tolerance: float = 0.005

    quote_refresh_seconds: float = 60.0
    bars_refresh_seconds: float = 21600.0
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
    def cross_validation_active(self) -> bool:
        return bool(self.cross_validation_enabled and self.tushare_token.strip())

    @model_validator(mode="after")
    def _validate(self) -> "CollectorSettings":
        invalid = [period for period in self.period_list if period not in SUPPORTED_PERIODS]
        if invalid:
            raise ValueError(
                f"unsupported COLLECTOR_COLLECT_PERIODS: {', '.join(invalid)}"
            )
        if self.cross_validation_tolerance < 0:
            raise ValueError("COLLECTOR_CROSS_VALIDATION_TOLERANCE must be >= 0")
        if self.history_days <= 0:
            raise ValueError("COLLECTOR_HISTORY_DAYS must be positive")
        if self.bars_history_days <= 0:
            raise ValueError("COLLECTOR_BARS_HISTORY_DAYS must be positive")
        if self.quote_refresh_seconds <= 0:
            raise ValueError("COLLECTOR_QUOTE_REFRESH_SECONDS must be positive")
        if self.bars_refresh_seconds <= 0:
            raise ValueError("COLLECTOR_BARS_REFRESH_SECONDS must be positive")
        if self.market_source not in {"akshare", "tushare"}:
            raise ValueError("COLLECTOR_MARKET_SOURCE must be 'akshare' or 'tushare'")
        if self.tushare_adjust.lower() not in {"", "qfq", "hfq"}:
            raise ValueError("COLLECTOR_TUSHARE_ADJUST must be '', 'qfq', or 'hfq'")
        if self.market_source == "tushare" and not self.tushare_token.strip():
            raise ValueError("COLLECTOR_TUSHARE_TOKEN is required when market_source is 'tushare'")
        if self.financial_source not in {"jsonl", "tushare"}:
            raise ValueError("COLLECTOR_FINANCIAL_SOURCE must be 'jsonl' or 'tushare'")
        if self.financial_source == "tushare" and not self.tushare_token.strip():
            raise ValueError(
                "COLLECTOR_TUSHARE_TOKEN is required when financial_source is 'tushare'"
            )
        return self


@lru_cache
def get_settings() -> CollectorSettings:
    return CollectorSettings()
