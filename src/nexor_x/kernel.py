from __future__ import annotations

import asyncio
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
from nexor_x.market.engine import MarketIntelligenceEngine
from nexor_x.evidence import EvidenceEngine
from nexor_x.quant import QuantBrain
from nexor_x.laboratory import LaboratoryService
from nexor_x.portfolio import PortfolioService
from nexor_x.risk import PreTradeGate


class Kernel:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.event_bus = EventBus()
        self.registry = ServiceRegistry()
        self.database = DatabaseService(settings.nexor_database_path)
        self.binance = BinanceMarketDataService(
            settings.binance_testnet,
            cache_ttl_seconds=settings.market_cache_ttl_seconds,
            stale_after_seconds=settings.market_stale_after_seconds,
            failure_cooldown_seconds=settings.market_failure_cooldown_seconds,
        )
        self.market_intelligence = MarketIntelligenceEngine()
        self.evidence_engine = EvidenceEngine()
        self.quant_brain = QuantBrain()
        self.laboratory = LaboratoryService(
            self.database, minimum_samples=settings.minimum_calibration_samples
        )
        self.portfolio = PortfolioService(self.database, settings.initial_paper_equity)
        self.pre_trade_gate = PreTradeGate(
            minimum_expected_r=settings.minimum_expected_r,
            minimum_profit_factor=settings.minimum_profit_factor,
            minimum_calibration_samples=settings.minimum_calibration_samples,
            risk_per_trade_pct=settings.risk_per_trade_pct,
            leverage=settings.leverage,
            max_open_positions=settings.max_open_positions,
            hard_stop_drawdown_pct=settings.hard_stop_drawdown_pct,
        )
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
            self.database,
            self.binance,
            self.telegram,
            self.ollama,
            self.scheduler,
            self.watchdog,
        ):
            await self.registry.register(service)

        self.event_bus.subscribe("*", self._persist_event)
        self.scheduler.add_job(ScheduledJob("kernel_heartbeat", 30.0, self._heartbeat))

        for service in (
            self.database,
            self.binance,
            self.telegram,
            self.ollama,
            self.scheduler,
        ):
            try:
                await service.start()
            except Exception as exc:
                service._state = ServiceState.FAILED
                service._details = str(exc)
                self._log.error("service_start_failed service=%s error=%s", service.name, exc)
        await self.watchdog.start()
        await self.portfolio.ensure_account()
        self._started = True
        await self.event_bus.publish(
            Event("system.started", {"mode": self.settings.nexor_mode.value}, "kernel")
        )
        await self.telegram.send(f"NEXOR X iniciado em modo {self.settings.nexor_mode.value}.")

    async def stop(self) -> None:
        if not self._started:
            return
        await self.event_bus.publish(Event("system.stopping", source="kernel"))
        for service in (self.watchdog, self.scheduler, self.ollama, self.telegram, self.binance):
            try:
                await service.stop()
            except Exception as exc:
                self._log.error("service_stop_failed service=%s error=%s", service.name, exc)
        await self.event_bus.stop()
        try:
            await self.database.stop()
        except Exception as exc:
            self._log.error("service_stop_failed service=%s error=%s", self.database.name, exc)
        self._started = False

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)

    async def status(self) -> dict[str, object]:
        services = await self.registry.health_snapshot()
        failed = any(s["state"] == ServiceState.FAILED.value for s in services)
        degraded = any(s["state"] == ServiceState.DEGRADED.value for s in services)
        return {
            "state": "DEGRADED" if failed or degraded else "ONLINE",
            "mode": self.settings.nexor_mode.value,
            "started": self._started,
            "event_queue": self.event_bus.pending_events,
            "services": services,
            "timestamp": datetime.now(UTC).isoformat(),
            "live_certified": False,
        }

    async def market_state(self, symbol: str) -> dict[str, object]:
        snapshot = await self.binance.market_snapshot(symbol)
        state = self.market_intelligence.classify(snapshot)
        await self.event_bus.publish(
            Event(
                "market.state",
                {
                    "symbol": state.symbol,
                    "regime": state.regime.value,
                    "direction": state.direction,
                    "confidence": state.confidence,
                    "stale": state.snapshot.stale,
                },
                "market_intelligence",
            )
        )
        return state.to_dict()


    async def quant_assessment(self, symbol: str) -> dict[str, object]:
        snapshot = await self.binance.market_snapshot(symbol)
        state = self.market_intelligence.classify(snapshot)
        evidences = self.evidence_engine.evaluate(state)
        preliminary = self.quant_brain.assess(state.symbol, evidences)
        calibration = await self.laboratory.estimate(
            preliminary.raw_edge, preliminary.decision.value, state.regime.value
        )
        assessment = self.quant_brain.assess(state.symbol, evidences, calibration)
        await self.event_bus.publish(
            Event(
                "quant.assessment",
                {
                    "symbol": assessment.symbol,
                    "decision": assessment.decision.value,
                    "raw_edge": assessment.raw_edge,
                    "calibrated": assessment.calibrated,
                    "expected_r": assessment.expected_r,
                    "execution_allowed": False,
                },
                "quant_brain",
            )
        )
        return assessment.to_dict()

    async def laboratory_status(self) -> dict[str, object]:
        return await self.laboratory.status()

    async def portfolio_status(self) -> dict[str, object]:
        return await self.portfolio.snapshot()

    async def trading_readiness(self, symbol: str) -> dict[str, object]:
        market = await self.market_state(symbol)
        quant = await self.quant_assessment(symbol)
        portfolio = await self.portfolio.snapshot()
        readiness = self.pre_trade_gate.evaluate(
            symbol=symbol,
            mode=self.settings.nexor_mode,
            market=market,
            quant=quant,
            portfolio=portfolio,
        )
        await self.event_bus.publish(
            Event(
                "risk.readiness",
                {
                    "symbol": symbol,
                    "decision": readiness.decision.value,
                    "allowed": readiness.allowed,
                    "side": readiness.side,
                    "risk_budget": readiness.risk_budget,
                },
                "pre_trade_gate",
            )
        )
        result = readiness.to_dict()
        result["portfolio"] = portfolio
        result["quant"] = {
            "decision": quant["decision"],
            "calibrated": quant["calibrated"],
            "expected_r": quant["expected_r"],
            "profit_factor": quant["profit_factor"],
            "calibration_samples": quant["calibration_samples"],
        }
        return result

    async def _heartbeat(self) -> None:
        await self.event_bus.publish(Event("system.heartbeat", source="kernel"))

    async def _persist_event(self, event: Event) -> None:
        if event.topic.startswith(("system.", "market.", "quant.", "laboratory.", "risk.")):
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
