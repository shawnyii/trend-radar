from datetime import datetime, timedelta, timezone

from app.models import Keyword, TrendObservation, TrendSnapshot
from app.services.spike_detection import build_spike_reason, detect_spikes_for_snapshot


def test_build_spike_reason_for_new_high_rank_keyword():
    reason = build_spike_reason(current_rank=3, previous=[], rank_threshold=10)
    assert reason == "new_keyword_high_rank"


def test_detect_spikes_creates_alert(db_session):
    now = datetime.now(timezone.utc)
    snapshot_old = TrendSnapshot(source="google", captured_at=now - timedelta(hours=2), status="success", raw_count=1)
    snapshot_new = TrendSnapshot(source="google", captured_at=now, status="success", raw_count=1)
    keyword = Keyword(
        keyword_text="AI",
        normalized_text="ai",
        first_seen_at=now - timedelta(hours=2),
        last_seen_at=now,
    )
    db_session.add_all([snapshot_old, snapshot_new, keyword])
    db_session.flush()

    db_session.add(
        TrendObservation(
            snapshot_id=snapshot_old.id,
            keyword_id=keyword.id,
            source_rank=25,
            source_value=1000,
            captured_at=now - timedelta(hours=2),
        )
    )
    db_session.add(
        TrendObservation(
            snapshot_id=snapshot_new.id,
            keyword_id=keyword.id,
            source_rank=5,
            source_value=10000,
            captured_at=now,
        )
    )
    db_session.commit()

    alerts = detect_spikes_for_snapshot(db_session, snapshot_new.id)
    db_session.commit()

    assert len(alerts) == 1
    assert alerts[0].trigger_reason == "rank_jump_vs_recent_average"
