"""initial schema

Revision ID: 20260426_0001
Revises:
Create Date: 2026-04-26 00:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = "20260426_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trend_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("raw_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_trend_snapshots_source", "trend_snapshots", ["source"])
    op.create_index("ix_trend_snapshots_captured_at", "trend_snapshots", ["captured_at"])

    op.create_table(
        "keywords",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("keyword_text", sa.String(length=255), nullable=False),
        sa.Column("normalized_text", sa.String(length=255), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("normalized_text", name="uq_keywords_normalized_text"),
    )
    op.create_index("ix_keywords_normalized_text", "keywords", ["normalized_text"])
    op.create_index("ix_keywords_last_seen_at", "keywords", ["last_seen_at"])

    op.create_table(
        "job_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_name", sa.String(length=100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
    )
    op.create_index("ix_job_runs_job_name", "job_runs", ["job_name"])

    op.create_table(
        "trend_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("trend_snapshots.id"), nullable=False),
        sa.Column("keyword_id", sa.Integer(), sa.ForeignKey("keywords.id"), nullable=False),
        sa.Column("source_rank", sa.Integer(), nullable=False),
        sa.Column("source_value", sa.Float(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("snapshot_id", "keyword_id", name="uq_observations_snapshot_keyword"),
    )
    op.create_index("ix_trend_observations_snapshot_id", "trend_observations", ["snapshot_id"])
    op.create_index("ix_trend_observations_keyword_id", "trend_observations", ["keyword_id"])
    op.create_index("ix_trend_observations_captured_at", "trend_observations", ["captured_at"])
    op.create_index(
        "ix_observations_keyword_captured_at",
        "trend_observations",
        ["keyword_id", "captured_at"],
    )

    op.create_table(
        "news_articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("keyword_id", sa.Integer(), sa.ForeignKey("keywords.id"), nullable=False),
        sa.Column("observation_id", sa.Integer(), sa.ForeignKey("trend_observations.id"), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("keyword_id", "url", name="uq_news_keyword_url"),
    )
    op.create_index("ix_news_articles_keyword_id", "news_articles", ["keyword_id"])
    op.create_index("ix_news_articles_observation_id", "news_articles", ["observation_id"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("keyword_id", sa.Integer(), sa.ForeignKey("keywords.id"), nullable=False),
        sa.Column("observation_id", sa.Integer(), sa.ForeignKey("trend_observations.id"), nullable=False),
        sa.Column("alert_type", sa.String(length=50), nullable=False),
        sa.Column("trigger_reason", sa.Text(), nullable=False),
        sa.Column("baseline_value", sa.Float(), nullable=True),
        sa.Column("current_value", sa.Float(), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notification_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.UniqueConstraint("dedupe_key", name="uq_alerts_dedupe_key"),
    )
    op.create_index("ix_alerts_keyword_id", "alerts", ["keyword_id"])
    op.create_index("ix_alerts_observation_id", "alerts", ["observation_id"])
    op.create_index("ix_alerts_triggered_at", "alerts", ["triggered_at"])


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("news_articles")
    op.drop_table("trend_observations")
    op.drop_table("job_runs")
    op.drop_table("keywords")
    op.drop_table("trend_snapshots")
