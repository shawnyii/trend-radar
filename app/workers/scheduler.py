from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.db import SessionLocal
from app.core.settings import get_settings
from app.workers.jobs import run_collection_pipeline, run_daily_summary


def _collection_job() -> None:
    with SessionLocal() as db:
        run_collection_pipeline(db)


def _summary_job() -> None:
    with SessionLocal() as db:
        run_daily_summary(db)


def build_scheduler() -> BackgroundScheduler:
    settings = get_settings()
    scheduler = BackgroundScheduler(timezone=settings.timezone)
    scheduler.add_job(
        _collection_job,
        trigger=IntervalTrigger(minutes=settings.collect_interval_minutes),
        id="collect_trends",
        replace_existing=True,
    )
    scheduler.add_job(
        _summary_job,
        trigger=CronTrigger(hour=settings.daily_summary_hour, minute=settings.daily_summary_minute),
        id="daily_summary",
        replace_existing=True,
    )
    return scheduler
