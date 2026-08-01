from __future__ import annotations
import asyncio
from collections.abc import Iterable
from nexor_x.core.service import Service

class ServiceRegistry:
    def __init__(self) -> None:
        self._services: dict[str, Service] = {}
        self._lock = asyncio.Lock()

    async def register(self, service: Service) -> None:
        async with self._lock:
            if service.name in self._services:
                raise ValueError(f"Service already registered: {service.name}")
            self._services[service.name] = service

    def all(self) -> Iterable[Service]:
        return tuple(self._services.values())

    async def health_snapshot(self) -> list[dict[str, object]]:
        results = await asyncio.gather(*(s.health() for s in self._services.values()))
        return [r.as_dict() for r in results]
