from datetime import datetime, timedelta, timezone

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.models import Alert, Keyword, TrendObservation


def detect_spikes_for_snapshot(db: Session, snapshot_id: int) -> list[Alert]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    lookback_cutoff = now - timedelta(hours=settings.spike_lookback_hours)
    dedupe_cutoff = now - timedelta(hours=settings.spike_dedupe_hours)

    observations = db.query(TrendObservation).filter(TrendObservation.snapshot_id == snapshot_id).all()
    alerts: list[Alert] = []

    for observation in observations:
        keyword = db.get(Keyword, observation.keyword_id)
        if keyword is None:
            continue

        previous = (
            db.query(TrendObservation)
            .filter(
                TrendObservation.keyword_id == observation.keyword_id,
                TrendObservation.captured_at >= lookback_cutoff,
                TrendObservation.snapshot_id != snapshot_id,
            )
            .order_by(TrendObservation.captured_at.desc())
            .all()
        )

        reason = build_spike_reason(observation.source_rank, previous, settings.spike_rank_threshold)
        if reason is None:
            continue

        dedupe_bucket = observation.captured_at.strftime("%Y%m%d%H")
        dedupe_key = f"{keyword.normalized_text}:{reason}:{dedupe_bucket}"

        existing = (
            db.query(Alert)
            .filter(and_(Alert.dedupe_key == dedupe_key, Alert.triggered_at >= dedupe_cutoff))
            .one_or_none()
        )
        if existing is not None:
            continue

        baseline_value = previous[0].source_value if previous else None
        current_value = observation.source_value
        alert = Alert(
            keyword_id=keyword.id,
            observation_id=observation.id,
            alert_type="spike",
            trigger_reason=reason,
            baseline_value=baseline_value,
            current_value=current_value,
            triggered_at=now,
            dedupe_key=dedupe_key,
        )
        db.add(alert)
        alerts.append(alert)

    return alerts


def build_spike_reason(current_rank: int, previous: list[TrendObservation], rank_threshold: int) -> str | None:
    if not previous and current_rank <= rank_threshold:
        return "new_keyword_high_rank"

    if previous:
        average_rank = sum(item.source_rank for item in previous) / len(previous)
        high_rank_streak = sum(1 for item in previous[:3] if item.source_rank <= rank_threshold)
        if average_rank - current_rank >= 10:
            return "rank_jump_vs_recent_average"
        if current_rank <= rank_threshold and high_rank_streak >= 2:
            return "sustained_high_rank"
    return None
