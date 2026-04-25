from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.models import Alert, Keyword, NewsArticle
from app.repositories.trends import get_latest_observations

DISCORD_CONTENT_LIMIT = 2000


def send_discord_message(content: str) -> bool:
    settings = get_settings()
    if not settings.discord_webhook_url:
        return False

    try:
        with httpx.Client(timeout=settings.request_timeout_seconds) as client:
            response = client.post(
                settings.discord_webhook_url,
                json={"content": truncate_discord_content(content)},
            )
            response.raise_for_status()
        return True
    except httpx.HTTPError:
        return False


def truncate_discord_content(content: str) -> str:
    if len(content) <= DISCORD_CONTENT_LIMIT:
        return content
    return content[: DISCORD_CONTENT_LIMIT - 20].rstrip() + "\n...[truncated]"


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
