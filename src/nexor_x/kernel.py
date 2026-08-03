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
from nexor_x.laboratory.monte_carlo import MonteCarloConfig
from nexor_x.portfolio import PortfolioService
from nexor_x.risk import PreTradeGate
from nexor_x.execution import PaperExecutionService
from nexor_x.scanner import MarketScannerService
from nexor_x.position import PositionManagementService
from nexor_x.position.service import PositionPolicy


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
            self.database, minimum_samples=settings.minimum_calibration_samples,
            minimum_expected_r=settings.minimum_expected_r,
            minimum_profit_factor=settings.minimum_profit_factor,
            maximum_fdr=settings.edge_discovery_maximum_fdr,
            probability_minimum_samples=settings.probability_minimum_samples,
            probability_holdout_fraction=settings.probability_holdout_fraction,
            probability_kelly_fraction=settings.probability_kelly_fraction,
            monte_carlo_minimum_observations=settings.monte_carlo_minimum_observations,
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
        self.paper_execution = PaperExecutionService(
            self.database, fee_rate=settings.paper_fee_rate,
            slippage_rate=settings.paper_slippage_rate,
            stop_loss_pct=settings.paper_stop_loss_pct,
            max_notional_multiple=settings.leverage,
        )
        self.position_management = PositionManagementService(
            self.database, self.paper_execution, PositionPolicy(
                break_even_trigger_r=settings.position_break_even_trigger_r,
                break_even_buffer_r=settings.position_break_even_buffer_r,
                partial_trigger_r=settings.position_partial_trigger_r,
                partial_fraction=settings.position_partial_fraction,
                trailing_start_r=settings.position_trailing_start_r,
                trailing_distance_r=settings.position_trailing_distance_r,
            )
        )
        self.scanner = MarketScannerService(
            self.database,
            self.quant_assessment,
            symbols=settings.scanner_symbol_list,
            concurrency=settings.scanner_concurrency,
            top_candidates=settings.scanner_top_candidates,
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
        if self.settings.scanner_enabled:
            self.scheduler.add_job(
                ScheduledJob(
                    "market_scanner",
                    self.settings.scanner_interval_seconds,
                    self._scheduled_scan,
                )
            )

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
        result = assessment.to_dict()
        result["market"] = state.to_dict()
        return result


    async def probability_assessment(self, symbol: str) -> dict[str, object]:
        snapshot = await self.binance.market_snapshot(symbol)
        state = self.market_intelligence.classify(snapshot)
        evidences = self.evidence_engine.evaluate(state)
        preliminary = self.quant_brain.assess(state.symbol, evidences)
        report = await self.laboratory.probability_estimate(
            preliminary.raw_edge, preliminary.decision.value, state.regime.value
        )
        result = report.to_dict()
        result.update({
            "symbol": state.symbol, "decision": preliminary.decision.value,
            "raw_edge": preliminary.raw_edge, "regime": state.regime.value,
            "data_stale": state.snapshot.stale,
        })
        await self.event_bus.publish(Event(
            "laboratory.probability_calibration",
            {"symbol": state.symbol, "decision": preliminary.decision.value,
             "ready": report.ready, "method": report.method,
             "sample_count": report.sample_count, "execution_allowed": False},
            "probability_calibration",
        ))
        return result

    async def scanner_run(self) -> dict[str, object]:
        run = await self.scanner.run_once()
        await self.event_bus.publish(
            Event(
                "scanner.completed",
                {
                    "run_id": run.run_id,
                    "symbols_requested": run.symbols_requested,
                    "symbols_succeeded": run.symbols_succeeded,
                    "symbols_failed": run.symbols_failed,
                    "candidate_count": len(run.candidates),
                    "execution_triggered": False,
                },
                "market_scanner",
            )
        )
        return run.to_dict()

    async def scanner_status(self) -> dict[str, object]:
        return await self.scanner.status()

    async def laboratory_status(self) -> dict[str, object]:
        return await self.laboratory.status()

    async def discover_edges(self) -> dict[str, object]:
        result = await self.laboratory.discover_edges()
        await self.event_bus.publish(Event(
            "laboratory.edge_discovery",
            {"run_id": result["run_id"], "discovered_count": result["discovered_count"],
             "candidate_count": result["candidate_count"], "execution_allowed": False},
            "edge_discovery",
        ))
        return result

    async def edge_status(self) -> dict[str, object]:
        return await self.laboratory.edge_status()

    async def run_monte_carlo(
        self, *, symbol: str | None = None, decision: str | None = None,
        regime: str | None = None, simulations: int | None = None,
        horizon_trades: int | None = None, block_size: int | None = None,
        seed: int | None = None,
    ) -> dict[str, object]:
        config = MonteCarloConfig(
            simulations=simulations or self.settings.monte_carlo_simulations,
            horizon_trades=horizon_trades or self.settings.monte_carlo_horizon_trades,
            block_size=block_size or self.settings.monte_carlo_block_size,
            starting_equity_r=self.settings.initial_paper_equity,
            ruin_drawdown_pct=self.settings.monte_carlo_ruin_drawdown_pct,
            seed=self.settings.monte_carlo_seed if seed is None else seed,
        )
        result = await self.laboratory.run_monte_carlo(
            config, symbol=symbol, decision=decision, regime=regime
        )
        await self.event_bus.publish(Event(
            "laboratory.monte_carlo",
            {
                "run_id": result["run_id"], "status": result["status"],
                "observation_count": result["observation_count"],
                "probability_of_ruin": result["probability_of_ruin"],
                "execution_allowed": False,
            },
            "monte_carlo",
        ))
        return result

    async def monte_carlo_status(self) -> dict[str, object]:
        return await self.laboratory.monte_carlo_status()


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


    async def paper_open(self, symbol: str) -> dict[str, object]:
        market = await self.market_state(symbol)
        readiness = await self.trading_readiness(symbol)
        portfolio = await self.portfolio.snapshot()
        fill = await self.paper_execution.open_from_readiness(
            mode=self.settings.nexor_mode, readiness=readiness, market=market, portfolio=portfolio
        )
        await self.event_bus.publish(Event("execution.paper_open", fill.to_dict(), "paper_execution"))
        return fill.to_dict()

    async def paper_close(self, position_id: int, market_price: float, reason: str) -> dict[str, object]:
        result = await self.paper_execution.close_position(position_id, market_price, reason)
        await self.event_bus.publish(Event("execution.paper_close", result, "paper_execution"))
        return result


    async def manage_position(self, position_id: int, market_price: float) -> dict[str, object]:
        result = await self.position_management.evaluate(position_id, market_price)
        await self.event_bus.publish(Event("position.managed", result, "position_management"))
        return result

    async def manage_all_positions(self) -> dict[str, object]:
        portfolio = await self.portfolio.snapshot()
        prices: dict[str, float] = {}
        for position in portfolio["positions"]:
            market = await self.market_state(str(position["symbol"]))
            snapshot = market.get("snapshot", {})
            if not snapshot.get("stale", True) and float(snapshot.get("price") or 0) > 0:
                prices[str(position["symbol"])] = float(snapshot["price"])
        result = await self.position_management.evaluate_all(prices)
        await self.event_bus.publish(Event("position.cycle", result, "position_management"))
        return result

    async def _heartbeat(self) -> None:
        await self.event_bus.publish(Event("system.heartbeat", source="kernel"))

    async def _scheduled_scan(self) -> None:
        try:
            await self.scanner_run()
        except Exception as exc:
            self._log.warning("scheduled_scan_failed error=%s", exc)

    async def _persist_event(self, event: Event) -> None:
        if event.topic.startswith(("system.", "market.", "quant.", "laboratory.", "risk.", "execution.", "position.")):
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
