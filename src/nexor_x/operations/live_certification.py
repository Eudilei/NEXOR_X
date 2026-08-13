from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class CertificationPolicy:
    min_days: int = 30
    min_closed_trades: int = 100
    min_profit_factor: float = 1.20
    max_drawdown_pct: float = 15.0


class LiveCertificationEvaluator:
    """Avalia evidências. Nunca autoriza execução LIVE."""

    def __init__(self, policy: CertificationPolicy | None = None) -> None:
        self.policy = policy or CertificationPolicy()

    def evaluate(
        self,
        *,
        readiness: dict[str, Any],
        validation_cycle: dict[str, Any],
        runtime: dict[str, Any],
    ) -> dict[str, Any]:
        days = self._number(
            validation_cycle,
            "days_running",
            "duration_days",
            "days",
            default=0.0,
        )
        closed_trades = self._number(
            validation_cycle,
            "closed_trades",
            "trades",
            "total_trades",
            default=0.0,
        )
        profit_factor = self._number(
            validation_cycle,
            "profit_factor",
            "pf",
            default=0.0,
        )
        drawdown_pct = self._drawdown_pct(validation_cycle)

        checks = {
            "readiness_passed": bool(readiness.get("candidate_ready", False)),
            "minimum_days": days >= self.policy.min_days,
            "minimum_closed_trades": (
                closed_trades >= self.policy.min_closed_trades
            ),
            "minimum_profit_factor": (
                profit_factor >= self.policy.min_profit_factor
            ),
            "maximum_drawdown": (
                0.0 <= drawdown_pct <= self.policy.max_drawdown_pct
            ),
            "runtime_live_disabled": not bool(
                runtime.get("live_enabled", False)
            ),
        }

        blockers = [name for name, ok in checks.items() if not ok]
        evidence_certified = not blockers

        return {
            "status": (
                "EVIDENCE_CERTIFIED"
                if evidence_certified
                else "EVIDENCE_INSUFFICIENT"
            ),
            "evidence_certified": evidence_certified,
            "live_allowed": False,
            "live_certified": False,
            "checks": checks,
            "blockers": blockers,
            "metrics": {
                "days_running": days,
                "closed_trades": closed_trades,
                "profit_factor": profit_factor,
                "max_drawdown_pct": drawdown_pct,
            },
            "policy": {
                "min_days": self.policy.min_days,
                "min_closed_trades": self.policy.min_closed_trades,
                "min_profit_factor": self.policy.min_profit_factor,
                "max_drawdown_pct": self.policy.max_drawdown_pct,
            },
            "evaluated_at": datetime.now(UTC).isoformat(),
            "safety_note": (
                "Certificação de evidências não é autorização para operar "
                "capital real. LIVE continua bloqueado."
            ),
        }

    @staticmethod
    def _number(
        payload: dict[str, Any],
        *keys: str,
        default: float,
    ) -> float:
        for key in keys:
            value = payload.get(key)
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return default

    def _drawdown_pct(self, payload: dict[str, Any]) -> float:
        direct = self._number(
            payload,
            "max_drawdown_pct",
            "drawdown_pct",
            default=-1.0,
        )
        if direct >= 0:
            return direct

        fractional = self._number(
            payload,
            "max_drawdown",
            "drawdown",
            default=-1.0,
        )
        if fractional < 0:
            return 100.0

        # Aceita tanto 0.12 quanto 12.0.
        return fractional * 100.0 if fractional <= 1.0 else fractional
