"""
libs.utils.scheduler — Обертка для APScheduler (фоновые задачи).

Пример использования:
    scheduler = SchedulerService()
    scheduler.add_interval(check_sensors, minutes=5)
    scheduler.add_cron(daily_report, hour=9, minute=0)
    await scheduler.start()
"""

from __future__ import annotations

from typing import Any, Callable, Awaitable

from loguru import logger


class SchedulerService:
    """Асинхронный планировщик задач на базе APScheduler."""

    def __init__(self) -> None:
        self._scheduler: Any = None
        self._jobs: list[dict[str, Any]] = []
        logger.info("SchedulerService инициализирован")

    # ── Ленивая инициализация ────────────────────────────────────────────

    def _get_scheduler(self) -> Any:
        if self._scheduler is not None:
            return self._scheduler

        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        self._scheduler = AsyncIOScheduler()
        return self._scheduler

    # ── Публичный API ────────────────────────────────────────────────────

    def add_interval(
        self,
        func: Callable[..., Awaitable[Any]] | Callable[..., Any],
        *,
        seconds: int = 0,
        minutes: int = 0,
        hours: int = 0,
        job_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Добавить задачу с интервальным запуском."""
        scheduler = self._get_scheduler()
        job = scheduler.add_job(
            func,
            "interval",
            seconds=seconds,
            minutes=minutes,
            hours=hours,
            id=job_id,
            **kwargs,
        )
        logger.info(
            "Scheduler: добавлена интервальная задача '{}' ({}с/{}м/{}ч)",
            job.id,
            seconds,
            minutes,
            hours,
        )
        return str(job.id)

    def add_cron(
        self,
        func: Callable[..., Awaitable[Any]] | Callable[..., Any],
        *,
        hour: int | str = "*",
        minute: int | str = "0",
        day_of_week: str = "*",
        job_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Добавить задачу по расписанию cron."""
        scheduler = self._get_scheduler()
        job = scheduler.add_job(
            func,
            "cron",
            hour=hour,
            minute=minute,
            day_of_week=day_of_week,
            id=job_id,
            **kwargs,
        )
        logger.info("Scheduler: добавлена cron-задача '{}' ({}:{} {})", job.id, hour, minute, day_of_week)
        return str(job.id)

    def add_once(
        self,
        func: Callable[..., Awaitable[Any]] | Callable[..., Any],
        *,
        run_date: Any = None,
        delay_seconds: float = 0,
        job_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Запустить задачу однократно (по дате или через N секунд)."""
        from datetime import datetime, timedelta, timezone

        scheduler = self._get_scheduler()

        if run_date is None:
            run_date = datetime.now(tz=timezone.utc) + timedelta(seconds=delay_seconds)

        job = scheduler.add_job(
            func,
            "date",
            run_date=run_date,
            id=job_id,
            **kwargs,
        )
        logger.info("Scheduler: однократная задача '{}' на {}", job.id, run_date)
        return str(job.id)

    def remove_job(self, job_id: str) -> None:
        """Удалить задачу по ID."""
        scheduler = self._get_scheduler()
        scheduler.remove_job(job_id)
        logger.info("Scheduler: удалена задача '{}'", job_id)

    def get_jobs(self) -> list[dict[str, Any]]:
        """Получить список всех задач."""
        scheduler = self._get_scheduler()
        jobs = scheduler.get_jobs()
        return [
            {
                "id": j.id,
                "name": j.name,
                "next_run": str(j.next_run_time),
                "trigger": str(j.trigger),
            }
            for j in jobs
        ]

    # ── Жизненный цикл ──────────────────────────────────────────────────

    async def start(self) -> None:
        """Запустить планировщик."""
        scheduler = self._get_scheduler()
        scheduler.start()
        logger.info("Scheduler: запущен ({} задач)", len(scheduler.get_jobs()))

    async def shutdown(self, wait: bool = True) -> None:
        """Остановить планировщик."""
        if self._scheduler:
            self._scheduler.shutdown(wait=wait)
            self._scheduler = None
            logger.info("Scheduler: остановлен")
