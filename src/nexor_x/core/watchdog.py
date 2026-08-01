from __future__ import annotations
import asyncio
from contextlib import suppress
from nexor_x.core.registry import ServiceRegistry
from nexor_x.core.service import BaseService
from nexor_x.domain import ServiceState
from nexor_x.logging import logger

class WatchdogService(BaseService):
    def __init__(self, registry: ServiceRegistry, interval_seconds: float = 10.0) -> None:
        super().__init__("watchdog")
        self._registry = registry
        self._interval = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._log = logger("watchdog")

    async def start(self) -> None:
        self._state = ServiceState.HEALTHY
        self._details = f"monitoring every {self._interval}s"
        self._task = asyncio.create_task(self._monitor())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        self._state = ServiceState.STOPPED

    async def _monitor(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            for service in self._registry.all():
                if service is self:
                    continue
                health = await service.health()
                if health.state is ServiceState.FAILED:
                    self._log.error("service_failed service=%s details=%s", health.name, health.details)
