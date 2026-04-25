from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class TrendSnapshot(Base):
    __tablename__ = "trend_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(100), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(20), default="success")
    raw_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    observations: Mapped[list["TrendObservation"]] = relationship(back_populates="snapshot")


class Keyword(Base):
    __tablename__ = "keywords"
    __table_args__ = (UniqueConstraint("normalized_text", name="uq_keywords_normalized_text"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    keyword_text: Mapped[str] = mapped_column(String(255))
    normalized_text: Mapped[str] = mapped_column(String(255), index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    observations: Mapped[list["TrendObservation"]] = relationship(back_populates="keyword")
    news_articles: Mapped[list["NewsArticle"]] = relationship(back_populates="keyword")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="keyword")


class TrendObservation(Base):
    __tablename__ = "trend_observations"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "keyword_id", name="uq_observations_snapshot_keyword"),
        Index("ix_observations_keyword_captured_at", "keyword_id", "captured_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("trend_snapshots.id"), index=True)
    keyword_id: Mapped[int] = mapped_column(ForeignKey("keywords.id"), index=True)
    source_rank: Mapped[int] = mapped_column(Integer)
    source_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    snapshot: Mapped[TrendSnapshot] = relationship(back_populates="observations")
    keyword: Mapped[Keyword] = relationship(back_populates="observations")
    news_articles: Mapped[list["NewsArticle"]] = relationship(back_populates="observation")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="observation")


class NewsArticle(Base):
    __tablename__ = "news_articles"
    __table_args__ = (UniqueConstraint("keyword_id", "url", name="uq_news_keyword_url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    keyword_id: Mapped[int] = mapped_column(ForeignKey("keywords.id"), index=True)
    observation_id: Mapped[int] = mapped_column(ForeignKey("trend_observations.id"), index=True)
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(Text)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    keyword: Mapped[Keyword] = relationship(back_populates="news_articles")
    observation: Mapped[TrendObservation] = relationship(back_populates="news_articles")


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (UniqueConstraint("dedupe_key", name="uq_alerts_dedupe_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    keyword_id: Mapped[int] = mapped_column(ForeignKey("keywords.id"), index=True)
    observation_id: Mapped[int] = mapped_column(ForeignKey("trend_observations.id"), index=True)
    alert_type: Mapped[str] = mapped_column(String(50), default="spike")
    trigger_reason: Mapped[str] = mapped_column(Text)
    baseline_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    notification_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dedupe_key: Mapped[str] = mapped_column(String(255))

    keyword: Mapped[Keyword] = relationship(back_populates="alerts")
    observation: Mapped[TrendObservation] = relationship(back_populates="alerts")


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_name: Mapped[str] = mapped_column(String(100), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
