from __future__ import annotations

from typing import Any
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from nexor_x import __version__
from nexor_x.dashboard import COMMAND_CENTER_V2


class PaperCloseRequest(BaseModel):
    market_price: float = Field(gt=0)
    reason: str = Field(default="MANUAL", min_length=1, max_length=120)



class PositionManageRequest(BaseModel):
    market_price: float = Field(gt=0)

class MonteCarloRequest(BaseModel):
    symbol: str | None = Field(default=None, min_length=3, max_length=30)
    decision: str | None = Field(default=None, min_length=3, max_length=40)
    regime: str | None = Field(default=None, min_length=3, max_length=40)
    simulations: int | None = Field(default=None, ge=100, le=100000)
    horizon_trades: int | None = Field(default=None, ge=20, le=100000)
    block_size: int | None = Field(default=None, ge=1, le=10000)
    seed: int | None = None


class WalkForwardRequest(BaseModel):
    symbol: str | None = Field(default=None, min_length=3, max_length=30)
    decision: str | None = Field(default=None, min_length=3, max_length=40)
    regime: str | None = Field(default=None, min_length=3, max_length=40)
    folds: int | None = Field(default=None, ge=2, le=20)


class CounterfactualRequest(BaseModel):
    symbol: str | None = Field(default=None, min_length=3, max_length=30)
    decision: str | None = Field(default=None, min_length=3, max_length=40)
    regime: str | None = Field(default=None, min_length=3, max_length=40)
    edge_thresholds: list[float] | None = Field(default=None, min_length=1, max_length=20)


class StrategyMetricRequest(BaseModel):
    strategy_id: str = Field(min_length=2, max_length=80)
    sample_count: int = Field(ge=1, le=10000000)
    profit_factor: float = Field(ge=0, le=1000)
    expected_r: float = Field(ge=-100, le=100)
    win_rate: float = Field(ge=0, le=1)
    max_drawdown_r: float = Field(ge=0, le=100000)
    brier_score: float | None = Field(default=None, ge=0, le=1)
    walk_forward_pass_ratio: float | None = Field(default=None, ge=0, le=1)
    monte_carlo_ruin_probability: float | None = Field(default=None, ge=0, le=1)

class StrategyRankRequest(BaseModel):
    symbol: str = Field(min_length=3, max_length=30)
    regime: str = Field(min_length=3, max_length=40)
    decision: str = Field(min_length=3, max_length=40)
    current_strategy_id: str | None = Field(default=None, max_length=80)
    metrics: list[StrategyMetricRequest] = Field(min_length=1, max_length=100)

class AllocationCandidateRequest(BaseModel):
    strategy_id: str = Field(min_length=2, max_length=80)
    symbol: str = Field(min_length=3, max_length=30)
    direction: str = Field(min_length=3, max_length=40)
    score: float = Field(ge=-100, le=100)
    expected_r: float = Field(ge=-100, le=100)
    profit_factor: float = Field(ge=0, le=1000)
    walk_forward_pass_ratio: float = Field(ge=0, le=1)
    monte_carlo_ruin_probability: float = Field(ge=0, le=1)
    max_drawdown_r: float = Field(ge=0, le=100000)
    current_drawdown_pct: float = Field(default=0, ge=0, le=100)
    correlation_group: str = Field(default='DEFAULT', max_length=80)

class AllocationPlanRequest(BaseModel):
    portfolio_drawdown_pct: float = Field(ge=0, le=100)
    candidates: list[AllocationCandidateRequest] = Field(min_length=1, max_length=100)

class CertificationRequest(BaseModel):
    paper_trades: int = Field(ge=0, le=100000000)
    profit_factor: float = Field(ge=0, le=1000)
    expected_r: float = Field(ge=-100, le=100)
    maximum_drawdown_pct: float = Field(ge=0, le=100)
    walk_forward_pass_ratio: float = Field(ge=0, le=1)
    monte_carlo_ruin_probability: float = Field(ge=0, le=1)
    brier_score_oos: float = Field(ge=0, le=1)
    calibration_ece_oos: float = Field(ge=0, le=1)
    operational_incidents: int = Field(ge=0, le=1000000)
    critical_test_failures: int = Field(ge=0, le=1000000)
    days_in_paper: int = Field(ge=0, le=100000)
    recent_profit_factor: float = Field(ge=0, le=1000)
    recent_expected_r: float = Field(ge=-100, le=100)
    data_freshness_ok: bool
    reconciliation_ok: bool
    secrets_configured: bool
    live_connector_tested: bool
    manual_owner_approval: bool = False

class TestnetOrderCreateRequest(BaseModel):
    strategy_id: str = Field(min_length=2, max_length=80)
    signal_id: str = Field(min_length=2, max_length=120)
    symbol: str = Field(min_length=3, max_length=30)
    side: str = Field(pattern='^(BUY|SELL)$')
    order_type: str = Field(pattern='^(MARKET|LIMIT)$')
    quantity: float = Field(gt=0)
    price: float | None = Field(default=None, gt=0)
    reduce_only: bool = False
    client_order_id: str | None = Field(default=None, max_length=36)

class TestnetOrderLookupRequest(BaseModel):
    symbol: str = Field(min_length=3, max_length=30)
    client_order_id: str | None = Field(default=None, max_length=36)
    exchange_order_id: str | None = Field(default=None, max_length=64)

class OperationalSupervisorRequest(BaseModel):
    mode: str = Field(default='PAPER', max_length=20)
    recovery_ok: bool
    exchange_ready: bool
    certification_passed: bool
    live_connector_tested: bool
    data_freshness_ok: bool
    hard_stop_active: bool
    critical_test_failures: int = Field(ge=0, le=1000000)
    operational_incidents: int = Field(ge=0, le=1000000)

class IntegrationHealthRequest(BaseModel):
    database_ok: bool
    market_ok: bool
    scanner_ok: bool
    strategy_ok: bool
    allocation_ok: bool
    recovery_ok: bool
    supervisor_ok: bool
    certification_ok: bool
    update_registry_ok: bool
    testnet_connector_ok: bool
    critical_test_failures: int = Field(ge=0, le=1000000)
    operational_incidents: int = Field(ge=0, le=1000000)

class ValidationSnapshotRequest(BaseModel):
    paper_trades: int = Field(ge=0, le=100000000)
    profit_factor: float = Field(ge=0, le=1000)
    expected_r: float = Field(ge=-100, le=100)
    drawdown_pct: float = Field(ge=0, le=100)
    recent_profit_factor: float = Field(ge=0, le=1000)
    recent_expected_r: float = Field(ge=-100, le=100)
    walk_forward_pass_ratio: float = Field(ge=0, le=1)
    monte_carlo_ruin_probability: float = Field(ge=0, le=1)
    brier_score_oos: float = Field(ge=0, le=1)
    calibration_ece_oos: float = Field(ge=0, le=1)
    integration_healthy: bool
    recovery_ok: bool
    supervisor_paper_allowed: bool
    supervisor_testnet_allowed: bool
    operational_incidents: int = Field(ge=0, le=1000000)
    critical_test_failures: int = Field(ge=0, le=1000000)

class ValidationCampaignRequest(BaseModel):
    days_running: int = Field(ge=0, le=100000)
    paper_trades: int = Field(ge=0, le=100000000)
    profit_factor: float = Field(ge=0, le=1000)
    expected_r: float = Field(ge=-100, le=100)
    drawdown_pct: float = Field(ge=0, le=100)
    recent_profit_factor: float = Field(ge=0, le=1000)
    recent_expected_r: float = Field(ge=-100, le=100)
    operational_incidents: int = Field(ge=0, le=1000000)
    critical_test_failures: int = Field(ge=0, le=1000000)
    integration_healthy: bool
    recovery_ok: bool
    supervisor_paper_allowed: bool
    supervisor_testnet_allowed: bool

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


def create_app(kernel: Any) -> FastAPI:
    app = FastAPI(title="NEXOR X", version=__version__)

    async def require_admin(x_nexor_admin_token: str | None = Header(default=None)) -> None:
        expected = kernel.settings.admin_api_token
        if not expected:
            raise HTTPException(
                status_code=503,
                detail="Controle administrativo desabilitado: configure NEXOR_ADMIN_API_TOKEN.",
            )
        if not x_nexor_admin_token or not secrets.compare_digest(x_nexor_admin_token, expected):
            raise HTTPException(status_code=401, detail="Token administrativo invalido.")

    @app.get("/", response_class=HTMLResponse)
    async def command_center() -> str:
        return COMMAND_CENTER_V2

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "nexor-x", "version": __version__}

    @app.get("/api/status")
    async def status() -> dict[str, Any]:
        return await kernel.status()

    @app.get("/api/config")
    async def config() -> dict[str, Any]:
        return kernel.settings.public_dict()

    @app.get("/api/market/{symbol}")
    async def market(symbol: str) -> dict[str, Any]:
        try:
            return await kernel.market_state(symbol)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/quant/{symbol}")
    async def quant(symbol: str) -> dict[str, Any]:
        try:
            return await kernel.quant_assessment(symbol)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc


    @app.get("/api/probability/{symbol}")
    async def probability(symbol: str) -> dict[str, Any]:
        try:
            return await kernel.probability_assessment(symbol)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/market-diagnostics")
    async def market_diagnostics() -> dict[str, Any]:
        return kernel.binance.diagnostics()

    @app.get("/api/scanner/status")
    async def scanner_status() -> dict[str, Any]:
        return await kernel.scanner_status()

    @app.post("/api/scanner/run")
    async def scanner_run(_: None = Depends(require_admin)) -> dict[str, Any]:
        try:
            return await kernel.scanner_run()
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/laboratory/status")
    async def laboratory_status() -> dict[str, Any]:
        return await kernel.laboratory_status()

    @app.get("/api/edges/status")
    async def edge_status() -> dict[str, Any]:
        return await kernel.edge_status()

    @app.post("/api/edges/discover")
    async def discover_edges(_: None = Depends(require_admin)) -> dict[str, Any]:
        return await kernel.discover_edges()

    @app.get("/api/monte-carlo/status")
    async def monte_carlo_status() -> dict[str, Any]:
        return await kernel.monte_carlo_status()

    @app.post("/api/monte-carlo/run")
    async def monte_carlo_run(
        body: MonteCarloRequest, _: None = Depends(require_admin)
    ) -> dict[str, Any]:
        try:
            return await kernel.run_monte_carlo(
                symbol=body.symbol.upper() if body.symbol else None,
                decision=body.decision, regime=body.regime,
                simulations=body.simulations, horizon_trades=body.horizon_trades,
                block_size=body.block_size, seed=body.seed,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


    @app.get("/api/walk-forward/status")
    async def walk_forward_status() -> dict[str, Any]:
        return await kernel.walk_forward_status()

    @app.post("/api/walk-forward/run")
    async def walk_forward_run(
        body: WalkForwardRequest, _: None = Depends(require_admin)
    ) -> dict[str, Any]:
        try:
            return await kernel.run_walk_forward(
                symbol=body.symbol.upper() if body.symbol else None,
                decision=body.decision, regime=body.regime, folds=body.folds,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/counterfactual/status")
    async def counterfactual_status() -> dict[str, Any]:
        return await kernel.counterfactual_status()

    @app.post("/api/counterfactual/run")
    async def counterfactual_run(
        body: CounterfactualRequest, _: None = Depends(require_admin)
    ) -> dict[str, Any]:
        try:
            return await kernel.run_counterfactual(
                symbol=body.symbol.upper() if body.symbol else None,
                decision=body.decision, regime=body.regime,
                edge_thresholds=tuple(body.edge_thresholds) if body.edge_thresholds else None,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/strategies/status")
    async def strategy_status() -> dict[str, Any]:
        return await kernel.strategy_status()

    @app.post("/api/strategies/rank")
    async def strategy_rank(
        body: StrategyRankRequest, _: None = Depends(require_admin)
    ) -> dict[str, Any]:
        try:
            return await kernel.strategy_rank(body.model_dump())
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/allocation/status")
    async def allocation_status() -> dict[str, Any]:
        return await kernel.allocation_status()

    @app.post("/api/allocation/plan")
    async def allocation_plan(
        body: AllocationPlanRequest, _: None = Depends(require_admin)
    ) -> dict[str, Any]:
        try:
            return await kernel.allocation_plan(body.model_dump())
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/certification/status")
    async def certification_status() -> dict[str, Any]:
        return await kernel.certification_status()

    @app.post("/api/certification/evaluate")
    async def certification_evaluate(
        body: CertificationRequest, _: None = Depends(require_admin)
    ) -> dict[str, Any]:
        try:
            return await kernel.certification_evaluate(body.model_dump())
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/exchange/live-readiness")
    async def exchange_live_readiness(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.binance_live_readiness()

    @app.post("/api/exchange/testnet/orders")
    async def create_testnet_order(
        body: TestnetOrderCreateRequest,
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        try:
            return await kernel.testnet_order_create(body.model_dump())
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/system/updates")
    async def system_updates(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.update_status()

    @app.post("/api/exchange/testnet/orders/status")
    async def testnet_order_status(
        body: TestnetOrderLookupRequest,
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        try:
            return await kernel.testnet_order_status(body.model_dump())
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/exchange/testnet/orders/cancel")
    async def testnet_order_cancel(
        body: TestnetOrderLookupRequest,
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        try:
            return await kernel.testnet_order_cancel(body.model_dump())
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/recovery/status")
    async def recovery_status(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.recovery_status()

    @app.post("/api/recovery/reconcile")
    async def recovery_reconcile(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        try:
            return await kernel.recovery_reconcile()
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/supervisor/status")
    async def operational_supervisor_status(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.operational_supervisor_status()

    @app.post("/api/supervisor/evaluate")
    async def operational_supervisor_evaluate(
        body: OperationalSupervisorRequest,
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.operational_supervisor_evaluate(
            body.model_dump()
        )

    @app.get("/api/system/integration-health")
    async def integration_health_status(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.integration_health_status()

    @app.post("/api/system/integration-health/evaluate")
    async def integration_health_evaluate(
        body: IntegrationHealthRequest,
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.integration_health_evaluate(
            body.model_dump()
        )

    @app.get("/api/validation/status")
    async def validation_snapshot_status(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.validation_snapshot_status()

    @app.post("/api/validation/evaluate")
    async def validation_snapshot_evaluate(
        body: ValidationSnapshotRequest,
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.validation_snapshot_evaluate(
            body.model_dump()
        )

    @app.get("/api/validation/campaign/status")
    async def validation_campaign_status(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.validation_campaign_status()

    @app.post("/api/validation/campaign/evaluate")
    async def validation_campaign_evaluate(
        body: ValidationCampaignRequest,
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.validation_campaign_evaluate(
            body.model_dump()
        )

    @app.get("/api/validation/cycle/status")
    async def validation_cycle_status(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.validation_cycle_status()

    @app.post("/api/validation/cycle/run")
    async def validation_cycle_run(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.validation_cycle_run()

    @app.get("/api/validation/evidence")
    async def validation_evidence_collect(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.validation_evidence_collect()

    @app.get("/api/backtest/context/{symbol}")
    async def context_backtest_status(
        symbol: str,
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.context_backtest_status(symbol)

    @app.get("/api/validation/release-candidate")
    async def release_candidate_audit_status(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.release_candidate_audit_status()

    @app.get("/api/validation/final-snapshot")
    async def final_dashboard_snapshot_status(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.final_dashboard_snapshot_status()

    @app.get("/api/validation/final-completion")
    async def final_technical_completion_status(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.final_technical_completion_status()

    @app.get("/api/validation/final-campaign")
    async def final_validation_campaign_status(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.final_validation_campaign_status()

    @app.post("/api/validation/final-campaign/tick")
    async def final_validation_campaign_tick(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.final_validation_campaign_tick()

    @app.get("/api/operations/acceptance-audit")
    async def operational_acceptance_audit(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.operational_acceptance_audit()

    @app.get("/api/operations/readiness-summary")
    async def operational_readiness_summary(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.operational_readiness_summary()

    @app.get("/api/operations/entry-decision-trace")
    async def unified_entry_decision_trace(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.unified_entry_decision_trace()

    @app.get("/api/operations/entry-reservation")
    async def entry_reservation_status(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.entry_reservation_status()

    @app.get("/api/operations/exposure-ramp")
    async def probation_exposure_ramp_status(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.probation_exposure_ramp_status()

    @app.get("/api/operations/post-recovery-probation")
    async def post_recovery_probation_status(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.post_recovery_probation_status()

    @app.get("/api/operations/recovery-hysteresis")
    async def entry_recovery_hysteresis_status(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.entry_recovery_hysteresis_status()

    @app.get("/api/operations/entry-admission")
    async def entry_admission_status(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.entry_admission_status()

    @app.get("/api/operations/degradation")
    async def performance_degradation_status(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.performance_degradation_status()

    @app.get("/api/live/certification")
    async def live_certification_status(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.live_certification_status()

    @app.get("/api/live/readiness")
    async def live_readiness_status(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.live_readiness_status()

    @app.get("/api/system/credentials")
    async def external_credentials_status(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.external_credentials_status()

    @app.get("/api/system/runtime")
    async def runtime_status(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.runtime_status()

    @app.get("/api/execution/auto-paper/status")
    async def auto_paper_status(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        return await kernel.auto_paper_status()

    @app.post("/api/execution/auto-paper/run")
    async def auto_paper_run(
        _: None = Depends(require_admin),
    ) -> dict[str, Any]:
        try:
            return await kernel.auto_paper_run()
        except RuntimeError as exc:
            raise HTTPException(
                status_code=409,
                detail=str(exc),
            ) from exc

    @app.get("/api/portfolio/status")
    async def portfolio_status() -> dict[str, Any]:
        return await kernel.portfolio_status()

    @app.get("/api/trading/readiness/{symbol}")
    async def trading_readiness(symbol: str) -> dict[str, Any]:
        try:
            return await kernel.trading_readiness(symbol)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/api/paper/open/{symbol}")
    async def paper_open(symbol: str, _: None = Depends(require_admin)) -> dict[str, Any]:
        try:
            return await kernel.paper_open(symbol)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/api/paper/close/{position_id}")
    async def paper_close(position_id: int, body: PaperCloseRequest, _: None = Depends(require_admin)) -> dict[str, Any]:
        try:
            return await kernel.paper_close(position_id, body.market_price, body.reason)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


    @app.post("/api/positions/{position_id}/manage")
    async def manage_position(position_id: int, body: PositionManageRequest, _: None = Depends(require_admin)) -> dict[str, Any]:
        try:
            return await kernel.manage_position(position_id, body.market_price)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/positions/auto-manage/status")
    async def auto_position_management_status(_: None = Depends(require_admin)) -> dict[str, Any]:
        return await kernel.auto_position_management_status()

    @app.post("/api/positions/auto-manage/run")
    async def auto_position_management_run(_: None = Depends(require_admin)) -> dict[str, Any]:
        try:
            return await kernel.auto_position_management_run()
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/positions/manage-all")
    async def manage_all_positions(_: None = Depends(require_admin)) -> dict[str, Any]:
        try:
            return await kernel.manage_all_positions()
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/api/ai/chat")
    async def chat(body: ChatRequest, _: None = Depends(require_admin)) -> dict[str, str]:
        system_status = await kernel.status()
        context = (
            "Voce e o copiloto do NEXOR X. Nao invente dados nem prometa lucro. "
            f"Modo: {kernel.settings.nexor_mode.value}. Estado: {system_status['state']}."
        )
        return {"answer": await kernel.ollama.chat(body.message, context)}

    @app.websocket("/ws/status")
    async def status_socket(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                await websocket.send_json(await kernel.status())
                await kernel.sleep(2.0)
        except WebSocketDisconnect:
            return

    return app


COMMAND_CENTER = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NEXOR X Command Center</title><style>
:root{--bg:#080c13;--panel:#111826;--panel2:#0d1420;--line:#24334b;--text:#eaf0fa;--muted:#91a2ba;--ok:#25d07f;--warn:#ffb547;--bad:#ff6474;--accent:#42a5ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px Segoe UI,Arial,sans-serif}.top{height:64px;display:flex;align-items:center;padding:0 24px;border-bottom:1px solid var(--line);background:#0c121d}.brand{font-size:21px;font-weight:800;letter-spacing:1.5px}.brand span{color:var(--accent)}.mode{margin-left:auto;padding:7px 12px;border:1px solid #24553f;border-radius:8px;color:var(--ok);background:#10231b}.layout{display:grid;grid-template-columns:220px 1fr;min-height:calc(100vh - 64px)}aside{border-right:1px solid var(--line);padding:18px 12px;background:#0b111b}.nav{padding:12px;border-radius:8px;color:var(--muted);margin:4px}.nav.active{background:#172236;color:var(--text)}main{padding:22px}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}.label{color:var(--muted);font-size:12px;text-transform:uppercase}.value{font-size:23px;font-weight:750;margin-top:8px}.small{font-size:13px;color:var(--muted);margin-top:8px}.wide{grid-column:span 2}.services{margin-top:14px;display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.service{background:var(--panel2);border:1px solid var(--line);padding:10px;border-radius:8px}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px;background:var(--bad)}.dot.ok{background:var(--ok)}.dot.warn{background:var(--warn)}input[type=password]{width:100%;background:#0b111c;color:var(--text);border:1px solid var(--line);border-radius:8px;padding:10px;margin-top:8px}textarea{width:100%;height:92px;background:#0b111c;color:var(--text);border:1px solid var(--line);border-radius:8px;padding:10px}button{margin-top:8px;background:var(--accent);border:0;color:#06101e;font-weight:700;padding:10px 16px;border-radius:8px;cursor:pointer}pre{white-space:pre-wrap;color:#cad7e9;min-height:82px}.foot{margin-top:16px;color:var(--muted);font-size:12px}@media(max-width:900px){.layout{grid-template-columns:1fr}aside{display:none}.grid{grid-template-columns:1fr}.wide{grid-column:span 1}.services{grid-template-columns:1fr}}
</style></head><body><header class="top"><div class="brand">NEXOR <span>X</span></div><div class="mode" id="mode">PAPER</div></header><div class="layout"><aside><div class="nav active">Visao Geral</div><div class="nav">Mercado</div><div class="nav">Estrategias</div><div class="nav">Carteira</div><div class="nav">Laboratorio</div><div class="nav">IA</div><div class="nav">Configuracoes</div><div class="nav">Sistema</div></aside><main><div class="grid"><section class="card"><div class="label">Sistema</div><div class="value" id="system">Carregando</div></section><section class="card"><div class="label">Servicos</div><div class="value" id="count">-</div></section><section class="card"><div class="label">BTCUSDT</div><div class="value" id="btc">-</div><div class="small" id="source">Aguardando mercado</div></section><section class="card"><div class="label">Regime</div><div class="value" id="regime">-</div><div class="small" id="marketReason">-</div></section><section class="card"><div class="label">Direcao</div><div class="value" id="direction">-</div></section><section class="card"><div class="label">Confianca do classificador</div><div class="value" id="confidence">-</div><div class="small">Nao representa probabilidade de lucro.</div></section><section class="card"><div class="label">Volatilidade</div><div class="value" id="volatility">-</div></section><section class="card"><div class="label">Dados</div><div class="value" id="freshness">-</div></section><section class="card"><div class="label">Quant Brain</div><div class="value" id="edgeDecision">-</div><div class="small" id="edgeNote">Aguardando evidencias</div></section><section class="card"><div class="label">Edge bruto</div><div class="value" id="rawEdge">-</div><div class="small">Sinal interno; nao e probabilidade de lucro.</div></section><section class="card"><div class="label">Calibracao</div><div class="value" id="calibration">-</div><div class="small" id="calibrationNote">Aguardando laboratorio</div></section><section class="card"><div class="label">Expected R</div><div class="value" id="expectedR">-</div><div class="small">Somente aparece com amostra historica suficiente.</div></section><section class="card wide"><div class="label">Fechamento Técnico</div><div class="value" id="finalTechnicalStatus">Aguardando token</div><div class="small" id="finalTechnicalProgress">Campanha: -</div><div class="services"><div class="service"><b>Acceptance Audit</b><br><small id="finalAcceptance">-</small></div><div class="service"><b>Readiness</b><br><small id="finalReadiness">-</small></div><div class="service"><b>Evidence</b><br><small id="finalEvidence">-</small></div><div class="service"><b>Exposure</b><br><small id="finalExposure">-</small></div><div class="service"><b>LIVE</b><br><small id="finalLive">BLOQUEADO</small></div><div class="service"><b>Release Candidate</b><br><small id="releaseCandidateStatus">-</small></div><div class="service"><b>Pendências</b><br><small id="finalPending">-</small></div></div></section><section class="card wide"><div class="label">Scanner de mercado</div><div class="value" id="scannerState">Aguardando</div><div class="small" id="scannerSummary">Nenhuma varredura concluida.</div><div class="services" id="scannerCandidates"></div></section><section class="card wide"><div class="label">Saude dos modulos</div><div class="services" id="services"></div></section><section class="card wide"><div class="label">IA local (Ollama)</div><input id="adminToken" type="password" placeholder="Token administrativo"><textarea id="question" placeholder="Qual e o estado atual do sistema?"></textarea><button onclick="ask()">Perguntar</button><pre id="answer"></pre></section></div><div class="foot">NEXOR X 0.16.0 — Monte Carlo por blocos e diagnostico de robustez; LIVE continua bloqueado.</div></main></div><script>
function render(s){system.textContent=s.state;mode.textContent=s.mode;count.textContent=s.services.length;services.innerHTML=s.services.map(x=>`<div class="service"><span class="dot ${x.state==='HEALTHY'?'ok':x.state==='DEGRADED'?'warn':''}"></span><b>${x.name}</b><br><small>${x.state} — ${x.details||''}</small></div>`).join('')}
function connect(){const proto=location.protocol==='https:'?'wss':'ws';const ws=new WebSocket(`${proto}://${location.host}/ws/status`);ws.onmessage=e=>render(JSON.parse(e.data));ws.onclose=()=>setTimeout(connect,2000)}
async function market(){try{const r=await fetch('/api/market/BTCUSDT');const p=await r.json();if(!r.ok)throw new Error(p.detail||'Falha');btc.textContent='$ '+Number(p.snapshot.price).toLocaleString('pt-BR',{maximumFractionDigits:2});regime.textContent=p.regime;direction.textContent=p.direction;confidence.textContent=(p.confidence*100).toFixed(1)+'%';volatility.textContent=(p.volatility*100).toFixed(1)+'%';freshness.textContent=p.snapshot.stale?'CACHE ANTIGO':'ATUAL';source.textContent=p.snapshot.source;marketReason.textContent=p.rationale.join(' • ')}catch(e){btc.textContent='Indisponivel';regime.textContent='SEM DADOS';source.textContent=e.message}}
async function quant(){try{const r=await fetch('/api/quant/BTCUSDT');const q=await r.json();if(!r.ok)throw new Error(q.detail||'Falha');edgeDecision.textContent=q.decision;rawEdge.textContent=Number(q.raw_edge).toFixed(3);edgeNote.textContent=q.rationale.join(' • ');calibration.textContent=q.calibrated?'CALIBRADO':'NAO PRONTO';calibrationNote.textContent=q.calibration_samples+' observacoes';expectedR.textContent=q.expected_r===null?'-':Number(q.expected_r).toFixed(4)+' R'}catch(e){edgeDecision.textContent='INDISPONIVEL';edgeNote.textContent=e.message}}
async function scanner(){try{const r=await fetch('/api/scanner/status');const s=await r.json();if(!r.ok)throw new Error(s.detail||'Falha');scannerState.textContent=s.running?'VARRENDO':'PRONTO';if(!s.last_run){scannerSummary.textContent='Nenhuma varredura concluida.';scannerCandidates.innerHTML='';return}const x=s.last_run;scannerSummary.textContent=`${x.symbols_succeeded}/${x.symbols_requested} simbolos analisados • ${x.symbols_failed} falhas • sem execucao automatica`;scannerCandidates.innerHTML=x.candidates.map(c=>`<div class="service"><b>${c.symbol}</b><br><small>${c.decision} • edge ${Number(c.raw_edge).toFixed(3)} • rank ${Number(c.rank_score).toFixed(3)} • ${c.regime}</small></div>`).join('')}catch(e){scannerState.textContent='INDISPONIVEL';scannerSummary.textContent=e.message}}
async function releaseCandidate(){const token=adminToken.value;if(!token){releaseCandidateStatus.textContent='INFORME O TOKEN';return}try{const r=await fetch('/api/validation/release-candidate',{headers:{'X-NEXOR-ADMIN-TOKEN':token}});const x=await r.json();if(!r.ok)throw new Error(x.detail||'Falha');releaseCandidateStatus.textContent=x.status;}catch(e){releaseCandidateStatus.textContent='INDISPONIVEL'}}
async function finalTechnical(){const token=adminToken.value;if(!token){finalTechnicalStatus.textContent='INFORME O TOKEN';return}try{const r=await fetch('/api/validation/final-snapshot',{headers:{'X-NEXOR-ADMIN-TOKEN':token}});const x=await r.json();if(!r.ok)throw new Error(x.detail||'Falha');finalTechnicalStatus.textContent=x.status;finalTechnicalProgress.textContent=`Campanha: ${Number(x.validation_progress_percent).toFixed(1)}% • ${x.validation_passes}/${x.validation_required_passes} PASS`;finalAcceptance.textContent=x.acceptance_status;finalReadiness.textContent=x.candidate_ready?'CANDIDATE READY':'PENDENTE';finalEvidence.textContent=x.evidence_certified?'CERTIFICADO':'PENDENTE';finalExposure.textContent=(Number(x.exposure_multiplier)*100).toFixed(0)+'%';finalLive.textContent='BLOQUEADO';finalPending.textContent=(x.pending_requirements||[]).join(' • ')||'Nenhuma';}catch(e){finalTechnicalStatus.textContent='INDISPONIVEL';finalTechnicalProgress.textContent=e.message}}
async function ask(){finalTechnical();answer.textContent='Processando...';const token=adminToken.value;try{const r=await fetch('/api/ai/chat',{method:'POST',headers:{'Content-Type':'application/json','X-NEXOR-ADMIN-TOKEN':token},body:JSON.stringify({message:question.value})}).then(r=>r.json());answer.textContent=r.answer||r.detail}catch(e){answer.textContent='Falha ao consultar a IA.'}}
connect();market();quant();scanner();setInterval(()=>{market();quant();scanner();finalTechnical();releaseCandidate()},15000);
</script></body></html>"""
