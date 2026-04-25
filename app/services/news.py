from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import feedparser
import httpx
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.models import Keyword, NewsArticle, TrendObservation
from app.services.schemas import NewsItem


def fetch_news_for_keyword(keyword: str) -> list[NewsItem]:
    settings = get_settings()
    url = settings.news_rss_url_template.format(query=quote_plus(keyword))
    with httpx.Client(timeout=settings.request_timeout_seconds, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
    feed = feedparser.parse(response.text)
    items: list[NewsItem] = []
    for entry in feed.entries[: settings.news_limit_per_keyword]:
        published_at = None
        if getattr(entry, "published", None):
            try:
                published_at = parsedate_to_datetime(entry.published)
            except (TypeError, ValueError):
                published_at = None
        publisher = None
        if getattr(entry, "source", None):
            publisher = getattr(entry.source, "title", None)
        items.append(
            NewsItem(
                title=entry.title,
                url=entry.link,
                publisher=publisher,
                published_at=published_at,
            )
        )
    return items


def enrich_news_for_snapshot(db: Session, snapshot_id: int) -> int:
    settings = get_settings()
    observations = (
        db.query(TrendObservation)
        .filter(TrendObservation.snapshot_id == snapshot_id)
        .order_by(TrendObservation.source_rank.asc())
        .limit(settings.top_keywords_limit)
        .all()
    )
    inserted = 0
    for observation in observations:
        keyword = db.get(Keyword, observation.keyword_id)
        if keyword is None:
            continue
        for item in fetch_news_for_keyword(keyword.keyword_text):
            exists = (
                db.query(NewsArticle)
                .filter(NewsArticle.keyword_id == keyword.id, NewsArticle.url == item.url)
                .one_or_none()
            )
            if exists:
                continue
            db.add(
                NewsArticle(
                    keyword_id=keyword.id,
                    observation_id=observation.id,
                    title=item.title,
                    url=item.url,
                    publisher=item.publisher,
                    published_at=item.published_at,
                    fetched_at=datetime.utcnow(),
                )
            )
            inserted += 1
    return inserted
