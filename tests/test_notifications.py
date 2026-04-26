from datetime import datetime, timezone

from app.models import Alert, Keyword, NewsArticle, TrendObservation, TrendSnapshot
from app.services.notifications import (
    DISCORD_CONTENT_LIMIT,
    DISCORD_SUPPRESS_EMBEDS_FLAG,
    build_alert_payload,
    build_daily_summary_payload,
    prepare_discord_payload,
    truncate_discord_content,
)


def test_truncate_discord_content_keeps_short_message():
    assert truncate_discord_content("hello") == "hello"


def test_truncate_discord_content_limits_long_message():
    message = "x" * (DISCORD_CONTENT_LIMIT + 100)

    result = truncate_discord_content(message)

    assert len(result) <= DISCORD_CONTENT_LIMIT
    assert result.endswith("...[truncated]")


def test_prepare_discord_payload_truncates_content():
    payload = {"content": "x" * (DISCORD_CONTENT_LIMIT + 50), "flags": DISCORD_SUPPRESS_EMBEDS_FLAG}

    prepared = prepare_discord_payload(payload)

    assert len(prepared["content"]) <= DISCORD_CONTENT_LIMIT
    assert prepared["flags"] == DISCORD_SUPPRESS_EMBEDS_FLAG


def test_build_daily_summary_payload_wraps_content(db_session):
    payload = build_daily_summary_payload(db_session)

    assert "content" in payload
    assert "Trend Radar daily summary" in payload["content"]


def test_build_alert_payload_uses_masked_links_and_suppresses_embeds(db_session):
    now = datetime.now(timezone.utc)
    snapshot = TrendSnapshot(source="google", captured_at=now, status="success", raw_count=1)
    keyword = Keyword(keyword_text="AI", normalized_text="ai", first_seen_at=now, last_seen_at=now)
    db_session.add_all([snapshot, keyword])
    db_session.flush()

    observation = TrendObservation(
        snapshot_id=snapshot.id,
        keyword_id=keyword.id,
        source_rank=1,
        source_value=1000,
        captured_at=now,
    )
    db_session.add(observation)
    db_session.flush()

    alert = Alert(
        keyword_id=keyword.id,
        observation_id=observation.id,
        alert_type="spike",
        trigger_reason="rank_jump_vs_recent_average",
        baseline_value=100,
        current_value=1000,
        triggered_at=now,
        dedupe_key="ai:test",
    )
    article = NewsArticle(
        keyword_id=keyword.id,
        observation_id=observation.id,
        title="AI headline",
        url="https://example.com/news",
        publisher="Example",
        published_at=now,
        fetched_at=now,
    )
    db_session.add_all([alert, article])
    db_session.commit()

    payload = build_alert_payload(db_session, alert)

    assert payload["flags"] == DISCORD_SUPPRESS_EMBEDS_FLAG
    assert "[AI headline](https://example.com/news)" in payload["content"]
    assert "- AI headline: https://example.com/news" not in payload["content"]
