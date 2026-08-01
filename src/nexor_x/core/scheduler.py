from __future__ import annotations
import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from nexor_x.core.service import BaseService
from nexor_x.domain import ServiceState
from nexor_x.logging import logger

Job = Callable[[], Awaitable[None]]

@dataclass(frozen=True, slots=True)
class ScheduledJob:
    name: str
    interval_seconds: float
    function: Job

class SchedulerService(BaseService):
    def __init__(self) -> None:
        super().__init__("scheduler")
        self._jobs: dict[str, ScheduledJob] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._log = logger("scheduler")

    def add_job(self, job: ScheduledJob) -> None:
        if job.interval_seconds <= 0:
            raise ValueError("Interval must be positive")
        if job.name in self._jobs:
            raise ValueError(f"Job already exists: {job.name}")
        self._jobs[job.name] = job

    async def start(self) -> None:
        self._state = ServiceState.STARTING
        for job in self._jobs.values():
            self._tasks[job.name] = asyncio.create_task(self._run(job), name=job.name)
        self._state = ServiceState.HEALTHY
        self._details = f"{len(self._jobs)} jobs"

    async def stop(self) -> None:
        for task in self._tasks.values():
            task.cancel()
        for task in self._tasks.values():
            with suppress(asyncio.CancelledError):
                await task
        self._tasks.clear()
        self._state = ServiceState.STOPPED

    async def _run(self, job: ScheduledJob) -> None:
        while True:
            try:
                await job.function()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._log.error("scheduled_job_failed job=%s error=%s", job.name, exc)
            await asyncio.sleep(job.interval_seconds)
