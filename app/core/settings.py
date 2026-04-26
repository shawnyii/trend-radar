from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "Trend Radar"
    environment: str = "development"
    timezone: str = "Asia/Taipei"
    database_url: str = "sqlite:///./trend_radar.db"
    discord_webhook_url: str | None = None
    trends_rss_url: str = "https://trends.google.com/trending/rss?geo=TW"
    news_rss_url_template: str = (
        "https://news.google.com/rss/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    )
    collect_interval_minutes: int = Field(default=60, ge=5)
    daily_summary_hour: int = Field(default=1, ge=0, le=23)
    daily_summary_minute: int = Field(default=45, ge=0, le=59)
    spike_rank_threshold: int = Field(default=10, ge=1)
    spike_lookback_hours: int = Field(default=24, ge=1)
    spike_dedupe_hours: int = Field(default=12, ge=1)
    top_keywords_limit: int = Field(default=20, ge=1, le=100)
    news_limit_per_keyword: int = Field(default=3, ge=1, le=10)
    request_timeout_seconds: float = Field(default=15.0, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
