from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.core.db import Base, SessionLocal, engine
from app.main import app
from app.models import Keyword, TrendObservation, TrendSnapshot


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
