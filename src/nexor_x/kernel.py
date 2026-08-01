from __future__ import annotations
import json
from datetime import UTC, datetime
from nexor_x.ai.ollama import OllamaService
from nexor_x.config import Settings
from nexor_x.core.event_bus import EventBus
from nexor_x.core.registry import ServiceRegistry
from nexor_x.core.scheduler import ScheduledJob, SchedulerService
from nexor_x.core.watchdog import WatchdogService
from nexor_x.domain import Event, ServiceState
from nexor_x.infrastructure.binance import BinanceMarketDataService
from nexor_x.infrastructure.database import DatabaseService
from nexor_x.infrastructure.telegram import TelegramService
from nexor_x.logging import logger

class Kernel:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.event_bus = EventBus()
        self.registry = ServiceRegistry()
        self.database = DatabaseService(settings.nexor_database_path)
        self.binance = BinanceMarketDataService(settings.binance_testnet)
        self.telegram = TelegramService(settings.telegram_bot_token, settings.telegram_chat_id)
        self.ollama = OllamaService(settings.ollama_base_url, settings.ollama_model)
        self.scheduler = SchedulerService()
        self.watchdog = WatchdogService(self.registry)
        self._started = False
        self._log = logger("kernel")

    async def start(self) -> None:
        if self._started:
            return
        await self.event_bus.start()
        for service in (
            self.database, self.binance, self.telegram, self.ollama, self.scheduler, self.watchdog
        ):
            await self.registry.register(service)

        self.event_bus.subscribe("*", self._persist_event)
        self.scheduler.add_job(ScheduledJob("kernel_heartbeat", 30.0, self._heartbeat))

        for service in (self.database, self.binance, self.telegram, self.ollama, self.scheduler):
            try:
                await service.start()
            except Exception as exc:
                service._state = ServiceState.FAILED
                service._details = str(exc)
                self._log.error("service_start_failed service=%s error=%s", service.name, exc)
        await self.watchdog.start()
        self._started = True
        await self.event_bus.publish(
            Event("system.started", {"mode": self.settings.nexor_mode.value}, "kernel")
        )
        await self.telegram.send(f"NEXOR X iniciado em modo {self.settings.nexor_mode.value}.")

    async def stop(self) -> None:
        if not self._started:
            return
        await self.event_bus.publish(Event("system.stopping", source="kernel"))
        for service in reversed(tuple(self.registry.all())):
            try:
                await service.stop()
            except Exception as exc:
                self._log.error("service_stop_failed service=%s error=%s", service.name, exc)
        await self.event_bus.stop()
        self._started = False

    async def status(self) -> dict[str, object]:
        services = await self.registry.health_snapshot()
        failed = any(s["state"] == ServiceState.FAILED.value for s in services)
        return {
            "state": "DEGRADED" if failed else "ONLINE",
            "mode": self.settings.nexor_mode.value,
            "started": self._started,
            "event_queue": self.event_bus.pending_events,
            "services": services,
            "timestamp": datetime.now(UTC).isoformat(),
            "live_certified": False,
        }

    async def _heartbeat(self) -> None:
        await self.event_bus.publish(Event("system.heartbeat", source="kernel"))

    async def _persist_event(self, event: Event) -> None:
        if event.topic.startswith("system."):
            await self.database.execute(
                """INSERT OR IGNORE INTO system_events
                (event_id, topic, source, payload_json, occurred_at) VALUES (?, ?, ?, ?, ?)""",
                (
                    event.event_id,
                    event.topic,
                    event.source,
                    json.dumps(event.payload, ensure_ascii=False, default=str),
                    event.occurred_at.isoformat(),
                ),
            )
