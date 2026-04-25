from datetime import datetime, timezone
from xml.etree import ElementTree

import httpx

from app.core.settings import get_settings
from app.services.schemas import TrendingKeywordItem


def normalize_keyword(keyword: str) -> str:
    return " ".join(keyword.strip().lower().split())


def fetch_trending_keywords() -> list[TrendingKeywordItem]:
    settings = get_settings()
    with httpx.Client(timeout=settings.request_timeout_seconds, follow_redirects=True) as client:
        response = client.get(settings.trends_rss_url)
        response.raise_for_status()

    root = ElementTree.fromstring(response.text)
    channel = root.find("channel")
    if channel is None:
        return []

    items: list[TrendingKeywordItem] = []
    captured_at = datetime.now(timezone.utc)
    for rank, item in enumerate(channel.findall("item"), start=1):
        title = item.findtext("title")
        if not title:
            continue
        approx_traffic = item.findtext("{https://trends.google.com/trending/rss}approx_traffic")
        source_value = _parse_approx_traffic(approx_traffic)
        items.append(
            TrendingKeywordItem(
                keyword=title.strip(),
                rank=rank,
                source_value=source_value,
                captured_at=captured_at,
            )
        )
    return items


def _parse_approx_traffic(raw_value: str | None) -> float | None:
    if not raw_value:
        return None
    sanitized = raw_value.replace("+", "").replace(",", "").strip().upper()
    if sanitized.endswith("K"):
        return float(sanitized[:-1]) * 1000
    if sanitized.endswith("M"):
        return float(sanitized[:-1]) * 1_000_000
    digits = "".join(ch for ch in sanitized if ch.isdigit() or ch == ".")
    return float(digits) if digits else None
