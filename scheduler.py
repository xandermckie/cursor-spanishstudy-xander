"""APScheduler — run fetcher.run_refresh every 15 minutes."""

from __future__ import annotations

import atexit
import logging
import os
import threading
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_init_lock = threading.Lock()


def _run_refresh_with_context(app) -> None:
    with app.app_context():
        import fetcher

        try:
            fetcher.run_refresh()
        except Exception as exc:
            logger.exception("Scheduled refresh failed: %s", exc)


def init_scheduler(app, interval_minutes: int = 15, enabled: bool = True) -> None:
    """Start background refresh job when the app boots."""
    global _scheduler

    if not enabled:
        logger.info("Scheduler disabled.")
        return

    # In debug mode, Werkzeug spawns a reloader child process.
    # Only start the scheduler in the child (WERKZEUG_RUN_MAIN=true),
    # or in production where this env var is unset.
    if os.environ.get("WERKZEUG_RUN_MAIN") == "false":
        return

    with _init_lock:
        if _scheduler is not None:
            return

        scheduler = BackgroundScheduler(daemon=True)
        _scheduler = scheduler
        try:
            scheduler.add_job(
                func=lambda: _run_refresh_with_context(app),
                trigger="interval",
                minutes=interval_minutes,
                id="refresh_job",
                replace_existing=True,
                next_run_time=datetime.now(timezone.utc),
            )
            scheduler.start()
            atexit.register(lambda: scheduler.shutdown(wait=False))
        except Exception:
            _scheduler = None
            raise

    logger.info("Scheduler started: refresh every %s minutes.", interval_minutes)
