from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

from nexor_x import __version__
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
from nexor_x.notifications import TelegramEventNotifier
from nexor_x.operations import LiveReadinessEvaluator
from nexor_x.operations.live_certification import LiveCertificationEvaluator
from nexor_x.operations.performance_degradation import PerformanceDegradationGuard
from nexor_x.operations.entry_admission import EntryAdmissionController
from nexor_x.operations.recovery_hysteresis import RecoveryHysteresisController
from nexor_x.operations.post_recovery_probation import PostRecoveryProbationController
from nexor_x.operations.probation_exposure_ramp import ProbationExposureRamp
from nexor_x.operations.entry_reservation import AtomicEntryReservationGuard
from nexor_x.operations.entry_decision_trace import UnifiedEntryDecisionTrace
from nexor_x.operations.filter_rigidity import FilterRigidityMonitor
from nexor_x.operations.operational_readiness_summary import UnifiedOperationalReadinessSummary
from nexor_x.operations.operational_acceptance_audit import OperationalAcceptanceAudit
from nexor_x.validation.final_campaign import FinalValidationCampaignController
from nexor_x.validation.final_completion import FinalTechnicalCompletionGate
from nexor_x.validation.final_dashboard import FinalTechnicalDashboardSnapshot
from nexor_x.validation.release_candidate import ReleaseCandidateAudit
from nexor_x.logging import logger
from nexor_x.market.engine import MarketIntelligenceEngine
from nexor_x.evidence import EvidenceEngine
from nexor_x.quant import QuantBrain
from nexor_x.laboratory import LaboratoryService
from nexor_x.laboratory.monte_carlo import MonteCarloConfig
from nexor_x.laboratory.walk_forward import WalkForwardConfig
from nexor_x.laboratory.counterfactual import CounterfactualConfig
from nexor_x.portfolio import PortfolioService
from nexor_x.risk import PreTradeGate
from nexor_x.execution import PaperExecutionService
from nexor_x.scanner import MarketScannerService
from nexor_x.position import PositionManagementService
from nexor_x.position.service import PositionPolicy
from nexor_x.autopaper import AutoPaperService
from nexor_x.automanage import AutoPositionManagementService
from nexor_x.secrets import ExternalCredentialsStatusService
from nexor_x.pretrade_backtest import (
    ContextBacktestPolicy,
    ContextBacktestService,
)
from nexor_x.evidence import EvidenceCollector
from nexor_x.validation_cycle import ValidationCycleService
from nexor_x.campaign import ValidationCampaignService
from nexor_x.validation import ValidationSnapshotService
from nexor_x.integration import IntegrationHealthService
from nexor_x.supervisor import OperationalSupervisorService
from nexor_x.recovery import RecoveryGuardService
from nexor_x.orders import (
    OrderAuditRepository,
    TestnetOrderLifecycleService,
)
from nexor_x.update_engine import UpdateRegistryService
from nexor_x.orders import (
    OrderSide,
    OrderType,
    TestnetOrderRequest,
    TestnetOrderService,
)
from nexor_x.exchange import (
    BinanceCredentials,
    BinanceLiveConnector,
    BinanceLivePolicy,
)
from nexor_x.certification import CertificationPolicy, CertificationService
from nexor_x.allocation import AllocationService, AllocationPolicy
from nexor_x.strategy import StrategyOrchestrationService


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
        self.context_backtest = ContextBacktestService(
            self.database,
            self.laboratory,
            ContextBacktestPolicy(
                minimum_samples=settings.pretrade_backtest_minimum_samples,
                maximum_samples=settings.pretrade_backtest_maximum_samples,
                minimum_profit_factor=settings.pretrade_backtest_minimum_profit_factor,
                minimum_expected_r=settings.pretrade_backtest_minimum_expected_r,
                minimum_recent_profit_factor=settings.pretrade_backtest_minimum_recent_profit_factor,
                minimum_recent_expected_r=settings.pretrade_backtest_minimum_recent_expected_r,
                maximum_drawdown_r=settings.pretrade_backtest_maximum_drawdown_r,
                minimum_walk_forward_pass_ratio=settings.pretrade_backtest_minimum_walk_forward_pass_ratio,
                folds=settings.pretrade_backtest_folds,
            ),
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
        self.strategy_orchestration = StrategyOrchestrationService(self.database)
        self.allocation = AllocationService(
            self.database,
            AllocationPolicy(
                maximum_candidates=settings.allocation_maximum_candidates,
                maximum_weight_per_candidate=settings.allocation_maximum_weight_per_candidate,
                maximum_weight_per_correlation_group=settings.allocation_maximum_weight_per_correlation_group,
                minimum_score=settings.allocation_minimum_score,
                minimum_expected_r=settings.minimum_expected_r,
                minimum_profit_factor=settings.minimum_profit_factor,
                minimum_walk_forward_pass_ratio=settings.walk_forward_minimum_pass_ratio,
                maximum_ruin_probability=settings.allocation_maximum_ruin_probability,
                maximum_candidate_drawdown_r=settings.allocation_maximum_candidate_drawdown_r,
                maximum_portfolio_risk_pct=settings.risk_per_trade_pct,
                recovery_drawdown_trigger_pct=settings.allocation_recovery_drawdown_trigger_pct,
                hard_stop_drawdown_pct=settings.hard_stop_drawdown_pct,
                recovery_risk_multiplier=settings.allocation_recovery_risk_multiplier,
            ),
        )
        self.certification = CertificationService(
            self.database,
            CertificationPolicy(
                minimum_paper_trades=settings.certification_minimum_paper_trades,
                minimum_profit_factor=settings.certification_minimum_profit_factor,
                minimum_expected_r=settings.certification_minimum_expected_r,
                maximum_drawdown_pct=settings.certification_maximum_drawdown_pct,
                minimum_walk_forward_pass_ratio=settings.certification_minimum_walk_forward_pass_ratio,
                maximum_monte_carlo_ruin_probability=settings.certification_maximum_ruin_probability,
                maximum_brier_score_oos=settings.certification_maximum_brier_score_oos,
                maximum_calibration_ece_oos=settings.certification_maximum_ece_oos,
                maximum_operational_incidents=0,
                maximum_critical_test_failures=0,
                minimum_days_in_paper=settings.certification_minimum_days_in_paper,
                minimum_recent_profit_factor=settings.certification_minimum_recent_profit_factor,
                minimum_recent_expected_r=settings.certification_minimum_recent_expected_r,
            ),
        )
        self.binance_live = BinanceLiveConnector(
            BinanceCredentials(
                api_key=settings.binance_api_key,
                api_secret=settings.binance_api_secret,
            ),
            BinanceLivePolicy(
                base_url=settings.binance_live_base_url,
                testnet_url=settings.binance_testnet_base_url,
                timeout_seconds=settings.binance_live_timeout_seconds,
                recv_window_ms=settings.binance_recv_window_ms,
                maximum_time_drift_ms=settings.binance_maximum_time_drift_ms,
                use_testnet=settings.binance_use_testnet,
            ),
        )
        self.testnet_orders = TestnetOrderService(
            self.database,
            self.binance_live,
        )
        self.update_registry = UpdateRegistryService(self.database)
        self.testnet_order_lifecycle = TestnetOrderLifecycleService(
            self.binance_live
        )
        self.order_audit = OrderAuditRepository(self.database)
        self.recovery_guard = RecoveryGuardService(
            self.database,
            self.binance_live,
        )
        self.operational_supervisor = OperationalSupervisorService(self.database)
        self.integration_health = IntegrationHealthService(self.database)
        self.validation_snapshot = ValidationSnapshotService(self.database)
        self.validation_campaign = ValidationCampaignService(self.database)
        self.evidence_collector = EvidenceCollector(self.database)
        self.validation_cycle = ValidationCycleService(
            self.database,
            self.evidence_collector,
            self.validation_campaign,
        )
        self.external_credentials = ExternalCredentialsStatusService(settings)
        self.scanner = MarketScannerService(
            self.database,
            self.quant_assessment,
            symbols=settings.scanner_symbol_list,
            concurrency=settings.scanner_concurrency,
            top_candidates=settings.scanner_top_candidates,
        )
        self.auto_paper = AutoPaperService(
            self.database,
            scanner_run=self.scanner_run,
            trading_readiness=self.trading_readiness,
            paper_open=self.paper_open,
            portfolio_snapshot=self.portfolio.snapshot,
            maximum_entries_per_cycle=settings.auto_paper_maximum_entries_per_cycle,
        )
        self.auto_position_management = AutoPositionManagementService(
            self.database,
            self.manage_all_positions,
        )
        self.telegram = TelegramService(settings.telegram_bot_token, settings.telegram_chat_id)
        self.telegram_notifier = TelegramEventNotifier(
            self.telegram,
            enabled=settings.telegram_notifications_enabled,
        )
        self.ollama = OllamaService(settings.ollama_base_url, settings.ollama_model)
        self.scheduler = SchedulerService()
        self.watchdog = WatchdogService(self.registry)
        self.runtime_processes = None
        self.live_readiness_evaluator = LiveReadinessEvaluator()
        self.live_certification_evaluator = LiveCertificationEvaluator()
        self.performance_degradation_guard = PerformanceDegradationGuard()
        self.entry_admission_controller = EntryAdmissionController()
        self.entry_recovery_guard = RecoveryHysteresisController(
            state_path="data/entry_recovery_state.json"
        )
        self.post_recovery_probation = PostRecoveryProbationController(
            state_path="data/entry_probation_state.json"
        )
        self.probation_exposure_ramp = ProbationExposureRamp()
        self.entry_decision_trace = UnifiedEntryDecisionTrace()
        self.filter_rigidity_monitor = FilterRigidityMonitor(
            state_path="data/filter_rigidity_state.json"
        )
        self.operational_readiness_summary = UnifiedOperationalReadinessSummary()
        self.operational_acceptance_audit = OperationalAcceptanceAudit()
        self.final_technical_completion = FinalTechnicalCompletionGate()
        self.final_dashboard_snapshot = FinalTechnicalDashboardSnapshot()
        self.release_candidate_audit = ReleaseCandidateAudit()
        self.final_validation_campaign = FinalValidationCampaignController(
            state_path="data/final_validation_campaign.json"
        )
        self.entry_reservation_guard = AtomicEntryReservationGuard(
            state_path="data/entry_reservation_state.json"
        )
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
        self.telegram_notifier.subscribe(self.event_bus)
        self.scheduler.add_job(ScheduledJob("kernel_heartbeat", 30.0, self._heartbeat))
        self.scheduler.add_job(
            ScheduledJob(
                "validation_cycle",
                900.0,
                self._scheduled_validation_cycle,
            )
        )
        if self.settings.auto_position_management_enabled:
            self.scheduler.add_job(
                ScheduledJob(
                    'auto_position_management_cycle',
                    self.settings.auto_position_management_interval_seconds,
                    self._scheduled_auto_position_management,
                )
            )
        if self.settings.auto_paper_enabled:
            self.scheduler.add_job(
                ScheduledJob(
                    'auto_paper_cycle',
                    self.settings.auto_paper_interval_seconds,
                    self._scheduled_auto_paper,
                )
            )
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
        await self.auto_paper.start()
        await self.auto_position_management.start()
        await self.context_backtest.start()
        await self.validation_campaign.start()
        await self.validation_cycle.start()
        await self.validation_snapshot.start()
        await self.integration_health.start()
        await self.operational_supervisor.start()
        await self.recovery_guard.start()
        await self.order_audit.start()
        await self.update_registry.start()
        await self.update_registry.register_runtime_version(
            version=__version__,
            update_id='23',
            source='runtime_startup',
        )
        await self.testnet_orders.start()
        await self.binance_live.start()
        await self.certification.start()
        await self.allocation.start()
        await self.strategy_orchestration.start()
        self._started = True
        await self.event_bus.publish(
            Event("system.started", {"mode": self.settings.nexor_mode.value}, "kernel")
        )

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
            "version": __version__,
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



    async def run_walk_forward(
        self, *, symbol: str | None = None, decision: str | None = None,
        regime: str | None = None, folds: int | None = None,
    ) -> dict[str, object]:
        config = WalkForwardConfig(
            folds=folds or self.settings.walk_forward_folds,
            minimum_train_observations=self.settings.walk_forward_minimum_train_observations,
            minimum_test_observations=self.settings.walk_forward_minimum_test_observations,
            minimum_pass_ratio=self.settings.walk_forward_minimum_pass_ratio,
            minimum_profit_factor=self.settings.walk_forward_minimum_profit_factor,
            minimum_expected_r=self.settings.minimum_expected_r,
        )
        result = await self.laboratory.run_walk_forward(
            config, symbol=symbol, decision=decision, regime=regime
        )
        await self.event_bus.publish(Event(
            "laboratory.walk_forward",
            {"run_id": result["run_id"], "status": result["status"],
             "passed_folds": result["passed_folds"], "folds_completed": result["folds_completed"],
             "execution_allowed": False},
            "walk_forward",
        ))
        return result

    async def walk_forward_status(self) -> dict[str, object]:
        return await self.laboratory.walk_forward_status()

    async def run_counterfactual(
        self, *, symbol: str | None = None, decision: str | None = None,
        regime: str | None = None, edge_thresholds: tuple[float, ...] | None = None,
    ) -> dict[str, object]:
        config = CounterfactualConfig(
            minimum_observations=self.settings.counterfactual_minimum_observations,
            minimum_kept_observations=self.settings.counterfactual_minimum_kept_observations,
            edge_thresholds=edge_thresholds or self.settings.counterfactual_edge_threshold_list,
        )
        result = await self.laboratory.run_counterfactual(
            config, symbol=symbol, decision=decision, regime=regime
        )
        await self.event_bus.publish(Event(
            "laboratory.counterfactual",
            {"run_id": result["run_id"], "status": result["status"],
             "best_scenario": result["best_scenario"], "causal_claim": False,
             "execution_allowed": False},
            "counterfactual",
        ))
        return result

    async def counterfactual_status(self) -> dict[str, object]:
        return await self.laboratory.counterfactual_status()

    async def strategy_status(self) -> dict[str, object]:
        return await self.strategy_orchestration.status()

    async def strategy_rank(self, payload: dict[str, object]) -> dict[str, object]:
        result = await self.strategy_orchestration.rank(
            symbol=str(payload['symbol']),
            regime=str(payload['regime']),
            decision=str(payload['decision']),
            metrics=list(payload.get('metrics') or []),
            current_strategy_id=(
                str(payload['current_strategy_id'])
                if payload.get('current_strategy_id') else None
            ),
        )
        await self.event_bus.publish(Event(
            'strategy.selection',
            {
                'symbol': result['symbol'],
                'selected_strategy_id': result['selected_strategy_id'],
                'status': result['status'],
                'execution_allowed': False,
            },
            'meta_strategy_orchestrator',
        ))
        return result

    async def allocation_status(self) -> dict[str, object]:
        return await self.allocation.status()

    async def allocation_plan(self, payload: dict[str, object]) -> dict[str, object]:
        result = await self.allocation.plan(
            portfolio_drawdown_pct=float(payload['portfolio_drawdown_pct']),
            candidates=list(payload.get('candidates') or []),
        )
        await self.event_bus.publish(Event(
            'portfolio.allocation_plan',
            {
                'status': result['status'],
                'total_weight': result['total_weight'],
                'total_risk_budget_pct': result['total_risk_budget_pct'],
                'execution_allowed': False,
            },
            'adaptive_portfolio_allocator',
        ))
        return result

    async def certification_status(self) -> dict[str, object]:
        return await self.certification.status()

    async def certification_evaluate(
        self, payload: dict[str, object]
    ) -> dict[str, object]:
        result = await self.certification.evaluate(payload)
        await self.event_bus.publish(Event(
            'certification.evaluated',
            {
                'status': result['status'],
                'passed': result['passed'],
                'live_execution_allowed': False,
            },
            'cqo_certification',
        ))
        return result

    async def binance_live_readiness(self) -> dict[str, object]:
        report = await self.binance_live.readiness()
        result = report.to_dict()
        await self.event_bus.publish(Event(
            'exchange.live_readiness',
            {
                'status': result['status'],
                'testnet': result['testnet'],
                'live_order_permission': False,
            },
            'binance_live_connector',
        ))
        return result

    async def testnet_order_create(
        self, payload: dict[str, object]
    ) -> dict[str, object]:
        with self.post_recovery_probation.successful_entry_transaction(
            action="TESTNET_CREATE_SUCCESS",
            bypass=bool(payload.get("reduce_only", False)),
        ):
            with self.entry_reservation_guard.transaction(
                action="TESTNET_CREATE_TRANSACTION",
                metadata={"symbol": payload.get("symbol")},
                bypass=bool(payload.get("reduce_only", False)),
            ):
                reduce_only = bool(payload.get("reduce_only", False))
                admission = await self.require_entry_admission(
                    action="TESTNET_CREATE",
                    reduce_only=reduce_only,
                )
                if not reduce_only and payload.get("quantity") is not None:
                    payload = dict(payload)
                    original_quantity = payload["quantity"]
                    payload["original_quantity"] = original_quantity
                    payload["quantity"] = self.probation_exposure_ramp.scale_quantity(
                        original_quantity,
                        float(admission.get("exposure_multiplier", 1.0)),
                    )
                    payload["exposure_multiplier"] = admission.get(
                        "exposure_multiplier", 1.0
                    )
                if not await self.recovery_guard.allows_testnet_orders():
                    raise RuntimeError(
                        'TESTNET orders locked: run recovery reconciliation first'
                    )
                request = TestnetOrderRequest(
                    symbol=str(payload['symbol']),
                    side=OrderSide(str(payload['side']).upper()),
                    order_type=OrderType(str(payload['order_type']).upper()),
                    quantity=float(payload['quantity']),
                    price=(None if payload.get('price') is None else float(payload['price'])),
                    reduce_only=reduce_only,
                    client_order_id=(
                        None if not payload.get('client_order_id')
                        else str(payload['client_order_id'])
                    ),
                )
                result = await self.testnet_orders.create(
                    strategy_id=str(payload['strategy_id']),
                    signal_id=str(payload['signal_id']),
                    request=request,
                )
                await self.event_bus.publish(Event(
                    'order.testnet_submitted',
                    {
                        'symbol': result['request']['symbol'],
                        'status': result['status'],
                        'duplicate': result['duplicate'],
                        'live_order_sent': False,
                    },
                    'testnet_order_service',
                ))
                return result

    async def update_status(self) -> dict[str, object]:
        return await self.update_registry.status()

    async def testnet_order_status(
        self, payload: dict[str, object]
    ) -> dict[str, object]:
        result = await self.testnet_order_lifecycle.status(
            symbol=str(payload['symbol']),
            client_order_id=(
                None if not payload.get('client_order_id')
                else str(payload['client_order_id'])
            ),
            exchange_order_id=(
                None if not payload.get('exchange_order_id')
                else str(payload['exchange_order_id'])
            ),
        )
        order = result['order']
        await self.order_audit.save(
            event_type='STATUS',
            symbol=order['symbol'],
            payload=result,
            client_order_id=order['client_order_id'],
            exchange_order_id=order['exchange_order_id'],
        )
        return result

    async def testnet_order_cancel(
        self, payload: dict[str, object]
    ) -> dict[str, object]:
        result = await self.testnet_order_lifecycle.cancel(
            symbol=str(payload['symbol']),
            client_order_id=(
                None if not payload.get('client_order_id')
                else str(payload['client_order_id'])
            ),
            exchange_order_id=(
                None if not payload.get('exchange_order_id')
                else str(payload['exchange_order_id'])
            ),
        )
        await self.order_audit.save(
            event_type='CANCEL',
            symbol=result['symbol'],
            payload=result,
            client_order_id=result['client_order_id'],
            exchange_order_id=result['exchange_order_id'],
        )
        return result

    async def recovery_status(self) -> dict[str, object]:
        return await self.recovery_guard.status()

    async def recovery_reconcile(self) -> dict[str, object]:
        result = await self.recovery_guard.reconcile()
        await self.event_bus.publish(Event(
            'recovery.reconciled',
            {
                'status': result['status'],
                'recovery_ok': result['recovery_ok'],
                'issue_count': len(result['issues']),
                'live_execution_allowed': False,
            },
            'recovery_guard',
        ))
        return result

    async def operational_supervisor_status(
        self,
    ) -> dict[str, object]:
        return await self.operational_supervisor.status()

    async def operational_supervisor_evaluate(
        self, payload: dict[str, object]
    ) -> dict[str, object]:
        result = await self.operational_supervisor.evaluate(payload)
        await self.event_bus.publish(Event(
            'supervisor.evaluated',
            {
                'status': result['status'],
                'paper_allowed': result['paper_allowed'],
                'testnet_allowed': result['testnet_allowed'],
                'live_allowed': False,
            },
            'operational_supervisor',
        ))
        return result

    async def integration_health_status(
        self,
    ) -> dict[str, object]:
        return await self.integration_health.status()

    async def integration_health_evaluate(
        self, payload: dict[str, object]
    ) -> dict[str, object]:
        result = await self.integration_health.evaluate(payload)
        await self.event_bus.publish(Event(
            'integration.health_evaluated',
            {
                'status': result['status'],
                'paper_ready': result['paper_ready'],
                'testnet_ready': result['testnet_ready'],
                'live_ready': False,
            },
            'integration_health',
        ))
        return result

    async def validation_snapshot_status(
        self,
    ) -> dict[str, object]:
        return await self.validation_snapshot.status()

    async def validation_snapshot_evaluate(
        self, payload: dict[str, object]
    ) -> dict[str, object]:
        result = await self.validation_snapshot.evaluate(payload)
        await self.event_bus.publish(Event(
            'validation.snapshot_evaluated',
            {
                'status': result['status'],
                'paper_validation_ready': result['paper_validation_ready'],
                'testnet_validation_ready': result['testnet_validation_ready'],
                'live_validation_ready': False,
            },
            'validation_snapshot',
        ))
        return result

    async def validation_campaign_status(
        self,
    ) -> dict[str, object]:
        return await self.validation_campaign.status()

    async def validation_campaign_evaluate(
        self, payload: dict[str, object]
    ) -> dict[str, object]:
        result = await self.validation_campaign.evaluate(payload)
        await self.event_bus.publish(Event(
            'validation.campaign_evaluated',
            {
                'phase': result['phase'],
                'continue_campaign': result['continue_campaign'],
                'paper_allowed': result['paper_allowed'],
                'testnet_allowed': result['testnet_allowed'],
                'live_allowed': False,
            },
            'validation_campaign',
        ))
        return result

    async def validation_cycle_status(
        self,
    ) -> dict[str, object]:
        return await self.validation_cycle.status()

    async def validation_cycle_run(
        self,
    ) -> dict[str, object]:
        result = await self.validation_cycle.run_once()
        await self.event_bus.publish(Event(
            'validation.cycle_completed',
            {
                'days_running': result['days_running'],
                'phase': result['campaign']['phase'],
                'live_allowed': False,
            },
            'validation_cycle',
        ))
        return result

    async def validation_evidence_collect(
        self,
    ) -> dict[str, object]:
        snapshot = await self.evidence_collector.collect()
        result = snapshot.to_dict()
        await self.event_bus.publish(Event(
            'validation.evidence_collected',
            {
                'paper_trades': result['paper_trades'],
                'integration_healthy': result['integration_healthy'],
                'recovery_ok': result['recovery_ok'],
                'live_allowed': False,
            },
            'evidence_collector',
        ))
        return result

    async def context_backtest_status(
        self, symbol: str | None = None,
    ) -> dict[str, object]:
        return await self.context_backtest.latest(symbol=symbol)

    async def release_candidate_audit_status(
        self,
    ) -> dict[str, object]:
        acceptance = await self.operational_acceptance_audit()
        final_snapshot = await self.final_dashboard_snapshot_status()
        components = {
            "live_readiness": hasattr(self, "live_readiness"),
            "live_certification": hasattr(self, "live_certification"),
            "performance_degradation": hasattr(self, "performance_degradation_guard"),
            "recovery_hysteresis": hasattr(self, "entry_recovery_guard"),
            "entry_admission": hasattr(self, "entry_admission_controller"),
            "post_recovery_probation": hasattr(self, "post_recovery_probation"),
            "exposure_ramp": hasattr(self, "probation_exposure_ramp"),
            "entry_reservation": hasattr(self, "entry_reservation_guard"),
            "entry_decision_trace": hasattr(self, "entry_decision_trace"),
            "operational_readiness_summary": hasattr(self, "operational_readiness_summary"),
            "operational_acceptance_audit": hasattr(self, "operational_acceptance_audit"),
            "final_validation_campaign": hasattr(self, "final_validation_campaign"),
            "final_technical_completion": hasattr(self, "final_technical_completion"),
            "final_dashboard_snapshot": hasattr(self, "final_dashboard_snapshot"),
        }
        return self.release_candidate_audit.evaluate(
            acceptance=acceptance,
            final_snapshot=final_snapshot,
            component_presence=components,
            version="0.56.0",
        )

    async def final_dashboard_snapshot_status(
        self,
    ) -> dict[str, object]:
        completion = await self.final_technical_completion_status()
        campaign = await self.final_validation_campaign_status()
        acceptance = await self.operational_acceptance_audit()
        readiness_summary = await self.operational_readiness_summary()
        return self.final_dashboard_snapshot.build(
            completion=completion,
            campaign=campaign,
            acceptance=acceptance,
            readiness_summary=readiness_summary,
        )

    async def final_technical_completion_status(
        self,
    ) -> dict[str, object]:
        acceptance = await self.operational_acceptance_audit()
        campaign = await self.final_validation_campaign_status()
        readiness = await self.live_readiness_status()
        certification = await self.live_certification_status()
        return self.final_technical_completion.evaluate(
            acceptance_audit=acceptance,
            campaign=campaign,
            readiness=readiness,
            certification=certification,
        )

    async def final_validation_campaign_status(
        self,
    ) -> dict[str, object]:
        return self.final_validation_campaign.status()

    async def final_validation_campaign_tick(
        self,
    ) -> dict[str, object]:
        audit = await self.operational_acceptance_audit()
        return self.final_validation_campaign.record(
            audit=audit,
        )

    async def operational_acceptance_audit(
        self,
    ) -> dict[str, object]:
        readiness = await self.live_readiness_status()
        certification = await self.live_certification_status()
        degradation = await self.performance_degradation_status()
        entry_trace = await self.unified_entry_decision_trace()
        summary = await self.operational_readiness_summary()
        return self.operational_acceptance_audit.run(
            readiness=readiness,
            certification=certification,
            degradation=degradation,
            entry_trace=entry_trace,
            summary=summary,
        )

    async def operational_readiness_summary(
        self,
    ) -> dict[str, object]:
        readiness = await self.live_readiness_status()
        certification = await self.live_certification_status()
        degradation = await self.performance_degradation_status()
        entry_trace = await self.unified_entry_decision_trace()
        return self.operational_readiness_summary.build(
            readiness=readiness,
            certification=certification,
            degradation=degradation,
            entry_trace=entry_trace,
        )

    async def filter_rigidity_status(
        self,
    ) -> dict[str, object]:
        return self.filter_rigidity_monitor.status()

    async def unified_entry_decision_trace(
        self,
    ) -> dict[str, object]:
        degradation = await self.performance_degradation_status()
        recovery = self.entry_recovery_guard.status()
        probation = self.post_recovery_probation.status()
        exposure = self.probation_exposure_ramp.evaluate(
            probation=probation,
            reduce_only=False,
        )
        reservation = self.entry_reservation_guard.status()
        return self.entry_decision_trace.build(
            degradation=degradation,
            recovery=recovery,
            probation=probation,
            exposure=exposure,
            reservation=reservation,
        )

    async def entry_reservation_status(
        self,
    ) -> dict[str, object]:
        return self.entry_reservation_guard.status()

    async def probation_exposure_ramp_status(
        self,
    ) -> dict[str, object]:
        probation = self.post_recovery_probation.status()
        return self.probation_exposure_ramp.evaluate(
            probation=probation, reduce_only=False
        )

    async def post_recovery_probation_status(
        self,
    ) -> dict[str, object]:
        return self.post_recovery_probation.status()

    async def entry_recovery_hysteresis_status(
        self,
    ) -> dict[str, object]:
        degradation = await self.performance_degradation_status()
        return self.entry_recovery_guard.evaluate(
            degradation=degradation,
        )

    async def entry_admission_status(
        self,
        *,
        action: str = "NEW_ENTRY",
        reduce_only: bool = False,
    ) -> dict[str, object]:
        degradation = await self.performance_degradation_status()
        recovery = self.entry_recovery_guard.evaluate(
            degradation=degradation,
        )
        if recovery["transition"] == "RECOVERED":
            self.post_recovery_probation.start()
        probation = self.post_recovery_probation.evaluate(
            degradation=recovery["degradation"],
            action=action,
            reduce_only=reduce_only,
        )
        report = self.entry_admission_controller.evaluate(
            degradation=probation["degradation"],
            action=action,
            reduce_only=reduce_only,
        )
        report["post_recovery_probation"] = {
            "active": probation["active"],
            "allowed": probation["allowed"],
            "block_reason": probation["block_reason"],
            "admitted_entries": probation["admitted_entries"],
            "max_entries_during_probation": (
                probation["max_entries_during_probation"]
            ),
            "remaining_seconds": probation["remaining_seconds"],
        }
        exposure = self.probation_exposure_ramp.evaluate(
            probation=probation, reduce_only=reduce_only
        )
        report["exposure_ramp"] = exposure
        report["exposure_multiplier"] = exposure["exposure_multiplier"]
        report["recovery_hysteresis"] = {
            "raw_state": recovery["raw_state"],
            "effective_state": recovery["effective_state"],
            "latched": recovery["latched"],
            "healthy_checks": recovery["healthy_checks"],
            "required_healthy_checks": recovery["required_healthy_checks"],
            "cooldown_seconds": recovery["cooldown_seconds"],
            "elapsed_since_block_seconds": recovery["elapsed_since_block_seconds"],
            "transition": recovery["transition"],
        }
        if recovery["transition"]:
            await self.event_bus.publish(Event(
                "execution.entry_recovery_state_changed",
                {
                    "transition": recovery["transition"],
                    "raw_state": recovery["raw_state"],
                    "effective_state": recovery["effective_state"],
                    "healthy_checks": recovery["healthy_checks"],
                    "new_entries_allowed": recovery["new_entries_allowed"],
                    "live_allowed": False,
                },
                "recovery_hysteresis_guard",
            ))
        if not report["allowed"]:
            await self.event_bus.publish(Event(
                "execution.entry_blocked_degradation",
                {
                    "action": report["action"],
                    "state": report["state"],
                    "reason": report["reason"],
                    "hard_reasons": report["hard_reasons"],
                    "live_allowed": False,
                },
                "entry_admission_guard",
            ))
        return report

    async def require_entry_admission(
        self,
        *,
        action: str,
        reduce_only: bool = False,
    ) -> dict[str, object]:
        report = await self.entry_admission_status(
            action=action,
            reduce_only=reduce_only,
        )
        if report["allowed"]:
            if not reduce_only:
                degradation = await self.performance_degradation_status()
                recovery = self.entry_recovery_guard.evaluate(
                    degradation=degradation,
                )
                probation = self.post_recovery_probation.evaluate(
                    degradation=recovery["degradation"],
                    action=action,
                    reduce_only=False,
                )
                if not probation["allowed"]:
                    raise RuntimeError(
                        "New entry blocked by post-recovery probation: "
                        + str(probation.get("block_reason") or "blocked")
                    )
                report["post_recovery_probation"] = {
                    "active": probation["active"],
                    "allowed": probation["allowed"],
                    "block_reason": probation["block_reason"],
                    "admitted_entries": probation["admitted_entries"],
                    "max_entries_during_probation": (
                        probation["max_entries_during_probation"]
                    ),
                    "remaining_seconds": probation["remaining_seconds"],
                }
                exposure = self.probation_exposure_ramp.evaluate(
                    probation=probation, reduce_only=False
                )
                report["exposure_ramp"] = exposure
                report["exposure_multiplier"] = exposure["exposure_multiplier"]
            return report
        reasons = list(report.get("hard_reasons") or [])
        raise RuntimeError(
            "New entry blocked by performance degradation: "
            + ", ".join(str(item) for item in reasons or ["blocked"])
        )

    async def performance_degradation_status(
        self,
    ) -> dict[str, object]:
        cycle = await self.validation_cycle_status()
        certification = await self.live_certification_status()
        report = self.performance_degradation_guard.evaluate(
            recent=cycle,
            certification=certification,
        )
        await self.event_bus.publish(Event(
            "operations.performance_degradation_evaluated",
            {
                "state": report["state"],
                "new_entries_allowed": report["new_entries_allowed"],
                "hard_reasons": report["hard_reasons"],
                "caution_reasons": report["caution_reasons"],
            },
            "performance_degradation",
        ))
        return report

    async def new_entries_allowed_by_performance(
        self,
    ) -> bool:
        report = await self.performance_degradation_status()
        return bool(report["new_entries_allowed"])

    async def live_certification_status(
        self,
    ) -> dict[str, object]:
        readiness = await self.live_readiness_status()
        cycle = await self.validation_cycle_status()
        runtime = await self.runtime_status()
        report = self.live_certification_evaluator.evaluate(
            readiness=readiness,
            validation_cycle=cycle,
            runtime=runtime,
        )
        await self.event_bus.publish(Event(
            "live.certification_evaluated",
            {
                "status": report["status"],
                "evidence_certified": report["evidence_certified"],
                "live_allowed": False,
                "blockers": report["blockers"],
            },
            "live_certification",
        ))
        return report

    async def live_readiness_status(
        self,
    ) -> dict[str, object]:
        credentials = await self.external_credentials_status()
        recovery = await self.recovery_status()
        supervisor = await self.operational_supervisor_status()
        integration = await self.integration_health_status()
        validation = await self.validation_snapshot_status()
        campaign = await self.validation_campaign_status()
        cycle = await self.validation_cycle_status()
        runtime = await self.runtime_status()
        report = self.live_readiness_evaluator.evaluate(
            mode=self.settings.nexor_mode.value,
            credentials=credentials,
            recovery=recovery,
            supervisor=supervisor,
            integration=integration,
            validation=validation,
            campaign=campaign,
            cycle=cycle,
            runtime=runtime,
        )
        await self.event_bus.publish(Event(
            "live.readiness_evaluated",
            {
                "status": report["status"],
                "candidate_ready": report["candidate_ready"],
                "live_allowed": False,
                "blockers": report["blockers"],
            },
            "live_readiness",
        ))
        return report

    async def external_credentials_status(
        self,
    ) -> dict[str, object]:
        return await self.external_credentials.status()

    async def runtime_status(self) -> dict[str, object]:
        if self.runtime_processes is None:
            return {
                'local_panel_url': f'http://127.0.0.1:{self.settings.nexor_port}',
                'public_panel_url': None,
                'ollama': {'running': False, 'details': 'Gerenciador não anexado.'},
                'cloudflared': {'running': False, 'details': 'Gerenciador não anexado.'},
                'live_enabled': False,
            }
        return await self.runtime_processes.status()

    async def auto_position_management_status(self) -> dict[str, object]:
        return await self.auto_position_management.status()

    async def auto_position_management_run(self) -> dict[str, object]:
        if self.settings.nexor_mode.value != 'PAPER':
            raise RuntimeError('Gestão automática permitida somente em PAPER')
        result = await self.auto_position_management.run_once()
        await self.event_bus.publish(Event('position.auto_management_cycle', {
            'evaluated_positions': result['evaluated_positions'],
            'action_count': result['action_count'],
            'closed_positions': result['closed_positions'],
            'live_execution_allowed': False,
        }, 'auto_position_management'))
        return result

    async def auto_paper_status(self) -> dict[str, object]:
        return await self.auto_paper.status()

    async def auto_paper_run(self) -> dict[str, object]:
        if self.settings.nexor_mode.value != 'PAPER':
            raise RuntimeError(
                'Execução automática permitida somente em PAPER'
            )
        result = await self.auto_paper.run_once()
        await self.event_bus.publish(Event(
            'execution.auto_paper_cycle',
            {
                'status': result['status'],
                'opened_positions': result['opened_positions'],
                'errors': result['errors'],
                'live_execution_allowed': False,
            },
            'auto_paper',
        ))
        return result

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
        contextual = await self.context_backtest.evaluate(
            symbol=symbol,
            decision=str(quant.get('decision') or 'NO_EDGE'),
            regime=str(market.get('regime') or 'UNKNOWN'),
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
                    "context_backtest_approved": contextual['approved'],
                },
                "pre_trade_gate",
            )
        )
        result = readiness.to_dict()
        result['context_backtest'] = contextual
        result['checks']['context_backtest'] = bool(contextual['approved'])
        if not contextual['approved']:
            result['allowed'] = False
            result['decision'] = 'BLOCKED'
            result['risk_budget'] = 0.0
            reasons = list(result.get('reasons') or [])
            reasons.append(
                'backtest contextual reprovado: '
                + ', '.join(contextual['blockers'])
            )
            result['reasons'] = reasons
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
        with self.post_recovery_probation.successful_entry_transaction(
            action="PAPER_OPEN_SUCCESS",
            bypass=False,
        ):
            with self.entry_reservation_guard.transaction(
                action="PAPER_OPEN_TRANSACTION",
                metadata={"symbol": symbol},
            ):
                await self.require_entry_admission(
                    action="PAPER_OPEN",
                    reduce_only=False,
                )
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

    async def _scheduled_validation_cycle(self) -> None:
        try:
            await self.validation_cycle_run()
        except Exception as exc:
            self._log.warning(
                'scheduled_validation_cycle_failed error=%s',
                exc,
            )

    async def _scheduled_auto_position_management(self) -> None:
        try:
            await self.auto_position_management_run()
        except Exception as exc:
            self._log.warning('scheduled_auto_position_management_failed error=%s', exc)

    async def _scheduled_auto_paper(self) -> None:
        try:
            await self.auto_paper_run()
        except Exception as exc:
            self._log.warning(
                'scheduled_auto_paper_failed error=%s',
                exc,
            )

    async def _scheduled_scan(self) -> None:
        try:
            await self.scanner_run()
        except Exception as exc:
            self._log.warning("scheduled_scan_failed error=%s", exc)

    async def _persist_event(self, event: Event) -> None:
        if event.topic.startswith(("system.", "market.", "quant.", "laboratory.", "risk.", "execution.", "position.", "strategy.")):
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
