from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.db import Base, SessionLocal, engine
from app.main import app
from app.models import Alert, JobRun, Keyword, TrendObservation, TrendSnapshot


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_latest_trends_endpoint():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        snapshot = TrendSnapshot(source="google", captured_at=now, status="success", raw_count=1)
        keyword = Keyword(keyword_text="Python", normalized_text="python", first_seen_at=now, last_seen_at=now)
        db.add_all([snapshot, keyword])
        db.flush()
        db.add(
            TrendObservation(
                snapshot_id=snapshot.id,
                keyword_id=keyword.id,
                source_rank=1,
                source_value=1000,
                captured_at=now,
            )
        )
        db.commit()

    client = TestClient(app)
    response = client.get("/api/trends/latest")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["keyword"] == "Python"


def test_keyword_detail_page_renders_datetime_series():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        snapshot = TrendSnapshot(source="google", captured_at=now, status="success", raw_count=1)
        keyword = Keyword(keyword_text="Python", normalized_text="python", first_seen_at=now, last_seen_at=now)
        db.add_all([snapshot, keyword])
        db.flush()
        db.add(
            TrendObservation(
                snapshot_id=snapshot.id,
                keyword_id=keyword.id,
                source_rank=1,
                source_value=1000,
                captured_at=now,
            )
        )
        db.commit()

    client = TestClient(app)
    response = client.get(f"/keywords/{keyword.id}")
    assert response.status_code == 200
    assert "Python" in response.text
    assert "Google Trends 排名（1 = 最熱門）" in response.text
    assert "precision: 0" in response.text
    assert "stepSize: 1" in response.text
    assert "排名：第 ${context.parsed.y} 名" in response.text


def test_favicon_returns_no_content():
    client = TestClient(app)
    response = client.get("/favicon.ico")
    assert response.status_code == 204


def test_recent_alerts_endpoint_returns_only_last_24_hours():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        snapshot = TrendSnapshot(source="google", captured_at=now, status="success", raw_count=1)
        keyword = Keyword(keyword_text="Python", normalized_text="python", first_seen_at=now, last_seen_at=now)
        db.add_all([snapshot, keyword])
        db.flush()
        observation = TrendObservation(
            snapshot_id=snapshot.id,
            keyword_id=keyword.id,
            source_rank=1,
            source_value=1000,
            captured_at=now,
        )
        db.add(observation)
        db.flush()
        db.add_all(
            [
                Alert(
                    keyword_id=keyword.id,
                    observation_id=observation.id,
                    alert_type="spike",
                    trigger_reason="recent",
                    triggered_at=now,
                    dedupe_key="recent",
                ),
                Alert(
                    keyword_id=keyword.id,
                    observation_id=observation.id,
                    alert_type="spike",
                    trigger_reason="old",
                    triggered_at=now - timedelta(days=2),
                    dedupe_key="old",
                ),
            ]
        )
        db.commit()

    client = TestClient(app)
    response = client.get("/api/alerts/recent")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["reason"] == "recent"


def test_system_status_endpoint_returns_latest_jobs():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        db.add_all(
            [
                JobRun(
                    job_name="collect_trends",
                    started_at=now,
                    finished_at=now,
                    status="success",
                    message="collected",
                ),
                JobRun(
                    job_name="daily_summary",
                    started_at=now,
                    finished_at=now,
                    status="success",
                    message="sent",
                ),
            ]
        )
        db.commit()

    client = TestClient(app)
    response = client.get("/api/system/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["latest_collect_job"]["status"] == "success"
    assert payload["latest_summary_job"]["message"] == "sent"
