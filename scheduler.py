"""APScheduler — run fetcher.run_refresh every 15 minutes."""

from __future__ import annotations

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler

import fetcher

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def init_scheduler(app, interval_minutes: int = 15, enabled: bool = True) -> None:
    """Start background refresh job when the app boots."""
    global _scheduler

    if not enabled:
        logger.info("Scheduler disabled.")
        return

    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler(daemon=True)

    def job():
        with app.app_context():
            try:
                fetcher.run_refresh()
            except Exception as exc:
                logger.exception("Scheduled refresh failed: %s", exc)

    _scheduler.add_job(
        job,
        "interval",
        minutes=interval_minutes,
        id="cache_refresh",
    )
    _scheduler.start()
    logger.info("Scheduler started: refresh every %s minutes.", interval_minutes)
