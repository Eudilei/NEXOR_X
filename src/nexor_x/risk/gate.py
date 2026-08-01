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
    ) -> None:
        self.minimum_expected_r = minimum_expected_r
        self.minimum_profit_factor = minimum_profit_factor
        self.minimum_calibration_samples = minimum_calibration_samples
        self.risk_per_trade_pct = risk_per_trade_pct
        self.leverage = leverage
        self.max_open_positions = max_open_positions
        self.hard_stop_drawdown_pct = hard_stop_drawdown_pct

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
        }
        reasons.extend(labels[key] for key, passed in checks.items() if not passed)

        if mode is OperatingMode.LIVE:
            decision = GateDecision.LIVE_FORBIDDEN
        elif not checks["below_hard_stop"]:
            decision = GateDecision.HARD_STOP
        elif all(checks.values()):
            decision = GateDecision.READY_FOR_PAPER
            reasons.append("contexto elegivel para simulacao PAPER; nenhuma ordem foi criada")
        else:
            decision = GateDecision.BLOCKED

        equity = float(portfolio.get("equity", 0.0))
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
