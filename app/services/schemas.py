from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class TrendingKeywordItem:
    keyword: str
    rank: int
    source_value: float | None
    captured_at: datetime


@dataclass(slots=True)
class NewsItem:
    title: str
    url: str
    publisher: str | None
    published_at: datetime | None
