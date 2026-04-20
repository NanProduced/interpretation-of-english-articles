"""
Daily article fetch scheduler.

Schedules daily article fetching at 9:00 AM UTC+8 (Asia/Shanghai).
Uses asyncio for scheduling without external dependencies.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from logging import getLogger
from typing import Any, Callable, Coroutine

from app.config.settings import get_settings

logger = getLogger(__name__)

UTC8 = timezone(timedelta(hours=8))


class DailyFetchScheduler:
    """
    Scheduler for daily article fetching.

    Runs at 9:00 AM UTC+8 every day.
    """

    def __init__(
        self,
        fetch_task: Callable[[], Coroutine[Any, Any, Any]],
        hour: int = 9,
        minute: int = 0,
        timezone: timezone = UTC8,
        enabled: bool = True,
    ):
        """
        Initialize the scheduler.

        Args:
            fetch_task: Async function to call when scheduled
            hour: Hour to run (24-hour format, default 9 for 9 AM)
            minute: Minute to run (default 0)
            timezone: Timezone for scheduling (default UTC+8)
            enabled: Whether the scheduler is enabled
        """
        self.fetch_task = fetch_task
        self.hour = hour
        self.minute = minute
        self.timezone = timezone
        self.enabled = enabled
        self._task: asyncio.Task[None] | None = None
        self._running = False

    def start(self) -> None:
        """Start the scheduler."""
        if not self.enabled:
            logger.info("Daily fetch scheduler is disabled in configuration")
            return

        if self._running:
            logger.warning("Daily fetch scheduler is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info(
            "Daily fetch scheduler started. Next run at %02d:%02d %s",
            self.hour,
            self.minute,
            self.timezone.tzname(None),
        )

    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Daily fetch scheduler stopped")

    def _get_next_run_time(self) -> datetime:
        """Calculate the next scheduled run time."""
        now = datetime.now(self.timezone)

        target = now.replace(
            hour=self.hour,
            minute=self.minute,
            second=0,
            microsecond=0,
        )

        if target <= now:
            target += timedelta(days=1)

        return target

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                next_run = self._get_next_run_time()
                now = datetime.now(self.timezone)
                wait_seconds = (next_run - now).total_seconds()

                logger.info(
                    "Next daily fetch scheduled for %s (in %.1f minutes)",
                    next_run.strftime("%Y-%m-%d %H:%M:%S %Z"),
                    wait_seconds / 60,
                )

                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)

                if self._running:
                    logger.info("Executing scheduled daily fetch task")
                    try:
                        await self.fetch_task()
                        logger.info("Scheduled daily fetch task completed")
                    except Exception as e:
                        logger.error("Scheduled daily fetch task failed: %s", e, exc_info=True)

            except asyncio.CancelledError:
                logger.info("Scheduler loop cancelled")
                break
            except Exception as e:
                logger.error("Unexpected error in scheduler loop: %s", e, exc_info=True)
                await asyncio.sleep(60)

    def health_snapshot(self) -> dict[str, Any]:
        """Get health status of the scheduler."""
        next_run = self._get_next_run_time() if self._running else None
        return {
            "enabled": self.enabled,
            "running": self._running,
            "scheduled_time": f"{self.hour:02d}:{self.minute:02d} {self.timezone.tzname(None)}",
            "next_run": next_run.isoformat() if next_run else None,
        }
