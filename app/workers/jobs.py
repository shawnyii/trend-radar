from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.services.ingest import ingest_trends, record_job_run
from app.services.news import enrich_news_for_snapshot
from app.services.notifications import build_alert_message, build_daily_summary, mark_alert_sent, send_discord_message
from app.services.spike_detection import detect_spikes_for_snapshot
from app.services.trends import fetch_trending_keywords


def run_collection_pipeline(db: Session) -> dict:
    started_at = datetime.now(timezone.utc)
    try:
        items = fetch_trending_keywords()
        snapshot = ingest_trends(db, items)
        news_count = enrich_news_for_snapshot(db, snapshot.id)
        alerts = detect_spikes_for_snapshot(db, snapshot.id)
        db.flush()

        sent_alerts = 0
        for alert in alerts:
            if send_discord_message(build_alert_message(db, alert)):
                mark_alert_sent(alert)
                sent_alerts += 1

        record_job_run(
            db,
            job_name="collect_trends",
            started_at=started_at,
            status="success",
            message=f"snapshot={snapshot.id} observations={snapshot.raw_count} news={news_count} alerts={len(alerts)} sent={sent_alerts}",
        )
        db.commit()
        return {
            "snapshot_id": snapshot.id,
            "observation_count": snapshot.raw_count,
            "news_count": news_count,
            "alerts_count": len(alerts),
            "sent_alerts_count": sent_alerts,
        }
    except Exception as exc:
        db.rollback()
        record_job_run(db, job_name="collect_trends", started_at=started_at, status="failed", message=str(exc))
        db.commit()
        raise


def run_daily_summary(db: Session) -> bool:
    started_at = datetime.now(timezone.utc)
    message = build_daily_summary(db)
    sent = send_discord_message(message)
    record_job_run(
        db,
        job_name="daily_summary",
        started_at=started_at,
        status="success" if sent else "skipped",
        message="sent" if sent else "discord_webhook_not_configured",
    )
    db.commit()
    return sent
