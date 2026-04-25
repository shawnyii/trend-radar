from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import JobRun, Keyword, TrendObservation, TrendSnapshot
from app.services.schemas import TrendingKeywordItem
from app.services.trends import normalize_keyword


def ingest_trends(db: Session, items: list[TrendingKeywordItem], source: str = "google_trends_tw") -> TrendSnapshot:
    captured_at = max((item.captured_at for item in items), default=datetime.now(timezone.utc))
    snapshot = TrendSnapshot(source=source, captured_at=captured_at, status="success", raw_count=len(items))
    db.add(snapshot)
    db.flush()

    for item in items:
        normalized_text = normalize_keyword(item.keyword)
        keyword = db.query(Keyword).filter(Keyword.normalized_text == normalized_text).one_or_none()
        if keyword is None:
            keyword = Keyword(
                keyword_text=item.keyword,
                normalized_text=normalized_text,
                first_seen_at=item.captured_at,
                last_seen_at=item.captured_at,
            )
            db.add(keyword)
            db.flush()
        else:
            keyword.keyword_text = item.keyword
            keyword.last_seen_at = item.captured_at

        db.add(
            TrendObservation(
                snapshot_id=snapshot.id,
                keyword_id=keyword.id,
                source_rank=item.rank,
                source_value=item.source_value,
                captured_at=item.captured_at,
            )
        )

    return snapshot


def record_job_run(db: Session, job_name: str, started_at: datetime, status: str, message: str | None = None) -> JobRun:
    job_run = JobRun(
        job_name=job_name,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc),
        status=status,
        message=message,
    )
    db.add(job_run)
    return job_run
