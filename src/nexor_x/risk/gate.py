from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from nexor_x.domain import OperatingMode

from .models import GateDecision, TradingReadiness


class PreTradeGate:
    """Single authoritative gate before any future order path.

    It accepts only causally calibrated, positive-expectancy contexts. Sprint 7 stops
    at readiness evaluation: no order is created even when PAPER readiness is true.
    """

    def __init__(
        self,
        *,
        minimum_expected_r: float,
        minimum_profit_factor: float,
        minimum_calibration_samples: int,
        risk_per_trade_pct: float,
        leverage: float,
        max_open_positions: int,
        hard_stop_drawdown_pct: float,
        maximum_open_risk_pct: float = 10.0,
        stop_loss_pct: float = 0.01,
        fee_rate: float = 0.0005,
        slippage_rate: float = 0.0003,
    ) -> None:
        self.minimum_expected_r = minimum_expected_r
        self.minimum_profit_factor = minimum_profit_factor
        self.minimum_calibration_samples = minimum_calibration_samples
        self.risk_per_trade_pct = risk_per_trade_pct
        self.leverage = leverage
        self.max_open_positions = max_open_positions
        self.hard_stop_drawdown_pct = hard_stop_drawdown_pct
        self.maximum_open_risk_pct = maximum_open_risk_pct
        self.stop_loss_pct = stop_loss_pct
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate

    def evaluate(
        self,
        *,
        symbol: str,
        mode: OperatingMode,
        market: dict[str, Any],
        quant: dict[str, Any],
        portfolio: dict[str, Any],
    ) -> TradingReadiness:
        directional = quant.get("decision") in {"LONG_BIAS", "SHORT_BIAS"}
        side = "LONG" if quant.get("decision") == "LONG_BIAS" else (
            "SHORT" if quant.get("decision") == "SHORT_BIAS" else None
        )
        calibrated = bool(quant.get("calibrated"))
        expected_r = quant.get("expected_r")
        pf = quant.get("profit_factor")
        samples = int(quant.get("calibration_samples") or 0)
        stale = bool(market.get("snapshot", {}).get("stale", True))
        drawdown = float(portfolio.get("drawdown_pct", 0.0))
        open_positions = int(portfolio.get("open_positions", 0))
        equity = float(portfolio.get("equity", 0.0))
        peak = float(portfolio.get("peak_equity", equity))
        open_risk = float(portfolio.get("open_risk_brl", 0.0)) + float(
            portfolio.get("gross_notional", 0.0)
        ) * (self.slippage_rate+self.fee_rate)
        candidate_budget = equity * (self.risk_per_trade_pct / 100.0)
        candidate_notional = min(
            candidate_budget/self.stop_loss_pct, equity*self.leverage
        ) if equity > 0 else 0.0
        candidate_reserve = candidate_notional * (
            self.stop_loss_pct+self.slippage_rate+2*self.fee_rate
        )
        projected_open_risk_pct = (
            (open_risk+candidate_reserve)/equity*100.0 if equity > 0 else 100.0
        )
        projected_drawdown_pct = (
            (peak-equity+open_risk+candidate_reserve)/peak*100.0 if peak > 0 else 100.0
        )

        checks = {
            "paper_mode": mode is OperatingMode.PAPER,
            "directional_edge": directional,
            "calibrated": calibrated,
            "minimum_samples": samples >= self.minimum_calibration_samples,
            "positive_expected_r": expected_r is not None and float(expected_r) >= self.minimum_expected_r,
            "profit_factor": pf is not None and float(pf) >= self.minimum_profit_factor,
            "fresh_market_data": not stale,
            "capacity_available": open_positions < self.max_open_positions,
            "below_hard_stop": drawdown < self.hard_stop_drawdown_pct,
            "portfolio_risk_available": projected_open_risk_pct <= self.maximum_open_risk_pct,
            "hard_stop_risk_reserve": projected_drawdown_pct < self.hard_stop_drawdown_pct,
        }
        reasons: list[str] = []
        labels = {
            "paper_mode": "modo LIVE permanece proibido",
            "directional_edge": "Quant Brain nao encontrou viés direcional",
            "calibrated": "contexto ainda nao foi calibrado causalmente",
            "minimum_samples": f"amostra abaixo de {self.minimum_calibration_samples}",
            "positive_expected_r": f"Expected R abaixo de {self.minimum_expected_r:.3f}",
            "profit_factor": f"Profit Factor abaixo de {self.minimum_profit_factor:.2f}",
            "fresh_market_data": "dados de mercado ausentes ou antigos",
            "capacity_available": "limite de posicoes atingido",
            "below_hard_stop": "hard stop de drawdown atingido",
            "portfolio_risk_available": "limite de risco agregado atingido",
            "hard_stop_risk_reserve": "nova entrada ultrapassaria o hard stop projetado",
        }
        reasons.extend(labels[key] for key, passed in checks.items() if not passed)

        if mode is OperatingMode.LIVE:
            decision = GateDecision.LIVE_FORBIDDEN
        elif not checks["below_hard_stop"] or not checks["hard_stop_risk_reserve"]:
            decision = GateDecision.HARD_STOP
        elif all(checks.values()):
            decision = GateDecision.READY_FOR_PAPER
            reasons.append("contexto elegivel para simulacao PAPER; nenhuma ordem foi criada")
        else:
            decision = GateDecision.BLOCKED

        risk_budget = equity * (self.risk_per_trade_pct / 100.0) if decision is GateDecision.READY_FOR_PAPER else 0.0
        return TradingReadiness(
            symbol=symbol,
            decision=decision,
            side=side,
            risk_budget=round(risk_budget, 8),
            leverage=self.leverage,
            checks=checks,
            reasons=tuple(reasons),
            evaluated_at=datetime.now(UTC),
        )
