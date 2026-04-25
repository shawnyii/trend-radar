from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.models import Alert, Keyword, NewsArticle
from app.repositories.trends import get_latest_observations


def send_discord_message(content: str) -> bool:
    settings = get_settings()
    if not settings.discord_webhook_url:
        return False

    with httpx.Client(timeout=settings.request_timeout_seconds) as client:
        response = client.post(settings.discord_webhook_url, json={"content": content})
        response.raise_for_status()
    return True


def build_daily_summary(db: Session) -> str:
    observations = get_latest_observations(db)
    if not observations:
        return "Trend Radar daily summary: no trend data collected yet."

    lines = ["Trend Radar daily summary", ""]
    for obs in observations[:10]:
        keyword = db.get(Keyword, obs.keyword_id)
        if keyword is None:
            continue
        value_suffix = f" ({int(obs.source_value)})" if obs.source_value else ""
        lines.append(f"{obs.source_rank}. {keyword.keyword_text}{value_suffix}")
    return "\n".join(lines)


def build_alert_message(db: Session, alert: Alert) -> str:
    keyword = db.get(Keyword, alert.keyword_id)
    if keyword is None:
        return "Trend Radar alert triggered."
    articles = (
        db.query(NewsArticle)
        .filter(NewsArticle.keyword_id == keyword.id)
        .order_by(NewsArticle.published_at.desc(), NewsArticle.fetched_at.desc())
        .limit(3)
        .all()
    )
    lines = [
        "Trend Radar spike alert",
        f"Keyword: {keyword.keyword_text}",
        f"Reason: {alert.trigger_reason}",
    ]
    for article in articles:
        lines.append(f"- {article.title}: {article.url}")
    return "\n".join(lines)


def mark_alert_sent(alert: Alert) -> None:
    alert.notification_sent_at = datetime.now(timezone.utc)
