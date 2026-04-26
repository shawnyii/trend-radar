from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import Alert, JobRun, Keyword, NewsArticle, TrendObservation, TrendSnapshot


def get_latest_snapshot(db: Session) -> TrendSnapshot | None:
    return db.scalar(select(TrendSnapshot).order_by(desc(TrendSnapshot.captured_at)).limit(1))


def get_latest_observations(db: Session, limit: int = 20) -> list[TrendObservation]:
    snapshot = get_latest_snapshot(db)
    if snapshot is None:
        return []
    stmt = (
        select(TrendObservation)
        .where(TrendObservation.snapshot_id == snapshot.id)
        .order_by(TrendObservation.source_rank.asc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def get_keyword_by_normalized_text(db: Session, normalized_text: str) -> Keyword | None:
    return db.scalar(select(Keyword).where(Keyword.normalized_text == normalized_text))


def get_keyword_series(db: Session, keyword_text: str, days: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(TrendObservation.captured_at, TrendObservation.source_rank, TrendObservation.source_value)
        .join(Keyword, Keyword.id == TrendObservation.keyword_id)
        .where(Keyword.normalized_text == keyword_text.strip().lower(), TrendObservation.captured_at >= cutoff)
        .order_by(TrendObservation.captured_at.asc())
    )
    return [
        {
            "captured_at": captured_at,
            "source_rank": source_rank,
            "source_value": source_value,
        }
        for captured_at, source_rank, source_value in db.execute(stmt).all()
    ]


def get_recent_alerts(db: Session, limit: int = 20) -> list[Alert]:
    stmt = select(Alert).order_by(desc(Alert.triggered_at)).limit(limit)
    return list(db.scalars(stmt))


def get_recent_alerts_24h(db: Session, limit: int = 20) -> list[Alert]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    stmt = select(Alert).where(Alert.triggered_at >= cutoff).order_by(desc(Alert.triggered_at)).limit(limit)
    return list(db.scalars(stmt))


def count_recent_alerts_24h(db: Session) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    return db.scalar(select(func.count(Alert.id)).where(Alert.triggered_at >= cutoff)) or 0


def get_keyword_news(db: Session, keyword_id: int, limit: int = 10) -> list[NewsArticle]:
    stmt = (
        select(NewsArticle)
        .where(NewsArticle.keyword_id == keyword_id)
        .order_by(desc(NewsArticle.published_at), desc(NewsArticle.fetched_at))
        .limit(limit)
    )
    return list(db.scalars(stmt))


def get_keyword_detail(db: Session, keyword_id: int) -> Keyword | None:
    return db.get(Keyword, keyword_id)


def get_dashboard_summary(db: Session) -> dict:
    latest = get_latest_snapshot(db)
    recent_alert_count = count_recent_alerts_24h(db)
    keyword_count = db.scalar(select(func.count(Keyword.id))) or 0
    latest_collect_job = get_latest_job_run(db, "collect_trends")
    latest_summary_job = get_latest_job_run(db, "daily_summary")
    return {
        "latest_snapshot": latest,
        "recent_alert_count": recent_alert_count,
        "keyword_count": keyword_count,
        "latest_collect_job": latest_collect_job,
        "latest_summary_job": latest_summary_job,
    }


def get_latest_job_run(db: Session, job_name: str) -> JobRun | None:
    stmt = select(JobRun).where(JobRun.job_name == job_name).order_by(desc(JobRun.started_at)).limit(1)
    return db.scalar(stmt)
