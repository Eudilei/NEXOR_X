from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class DegradationPolicy:
    min_recent_trades: int = 20
    caution_profit_factor: float = 1.20
    block_profit_factor: float = 1.00
    caution_drawdown_pct: float = 10.0
    block_drawdown_pct: float = 15.0
    caution_loss_streak: int = 4
    block_loss_streak: int = 6


class PerformanceDegradationGuard:
    """Avalia deterioração recente e decide se novas entradas são seguras."""

    def __init__(self, policy: DegradationPolicy | None = None) -> None:
        self.policy = policy or DegradationPolicy()

    def evaluate(
        self,
        *,
        recent: dict[str, Any],
        certification: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        recent_trades = int(self._number(
            recent,
            "recent_trades",
            "closed_trades",
            "trades",
            default=0.0,
        ))
        profit_factor = self._number(
            recent,
            "recent_profit_factor",
            "profit_factor",
            "pf",
            default=0.0,
        )
        drawdown_pct = self._drawdown_pct(recent)
        loss_streak = int(self._number(
            recent,
            "loss_streak",
            "consecutive_losses",
            "losing_streak",
            default=0.0,
        ))

        enough_sample = recent_trades >= self.policy.min_recent_trades

        hard_reasons: list[str] = []
        caution_reasons: list[str] = []

        if enough_sample:
            if profit_factor < self.policy.block_profit_factor:
                hard_reasons.append("profit_factor_below_1")
            elif profit_factor < self.policy.caution_profit_factor:
                caution_reasons.append("profit_factor_weak")

            if drawdown_pct >= self.policy.block_drawdown_pct:
                hard_reasons.append("drawdown_limit_reached")
            elif drawdown_pct >= self.policy.caution_drawdown_pct:
                caution_reasons.append("drawdown_elevated")

        if loss_streak >= self.policy.block_loss_streak:
            hard_reasons.append("loss_streak_critical")
        elif loss_streak >= self.policy.caution_loss_streak:
            caution_reasons.append("loss_streak_elevated")

        # Se já havia certificação e ela deixou de ser válida, trata como cautela.
        if certification is not None and not bool(
            certification.get("evidence_certified", False)
        ):
            caution_reasons.append("evidence_not_certified")

        if hard_reasons:
            state = "BLOCKED"
            new_entries_allowed = False
        elif caution_reasons:
            state = "CAUTION"
            new_entries_allowed = True
        else:
            state = "NORMAL"
            new_entries_allowed = True

        return {
            "state": state,
            "new_entries_allowed": new_entries_allowed,
            "manage_existing_positions": True,
            "live_allowed": False,
            "hard_reasons": hard_reasons,
            "caution_reasons": caution_reasons,
            "metrics": {
                "recent_trades": recent_trades,
                "profit_factor": profit_factor,
                "drawdown_pct": drawdown_pct,
                "loss_streak": loss_streak,
                "enough_sample": enough_sample,
            },
            "policy": {
                "min_recent_trades": self.policy.min_recent_trades,
                "caution_profit_factor": self.policy.caution_profit_factor,
                "block_profit_factor": self.policy.block_profit_factor,
                "caution_drawdown_pct": self.policy.caution_drawdown_pct,
                "block_drawdown_pct": self.policy.block_drawdown_pct,
                "caution_loss_streak": self.policy.caution_loss_streak,
                "block_loss_streak": self.policy.block_loss_streak,
            },
            "evaluated_at": datetime.now(UTC).isoformat(),
            "safety_note": (
                "O guard pode bloquear novas entradas, mas não desativa a "
                "gestão/proteção de posições existentes. LIVE permanece bloqueado."
            ),
        }

    def allow_new_entry(
        self,
        *,
        recent: dict[str, Any],
        certification: dict[str, Any] | None = None,
    ) -> bool:
        return bool(
            self.evaluate(
                recent=recent,
                certification=certification,
            )["new_entries_allowed"]
        )

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
            "recent_drawdown_pct",
            "max_drawdown_pct",
            "drawdown_pct",
            default=-1.0,
        )
        if direct >= 0:
            return direct

        fractional = self._number(
            payload,
            "recent_drawdown",
            "max_drawdown",
            "drawdown",
            default=0.0,
        )
        return fractional * 100.0 if 0.0 <= fractional <= 1.0 else fractional
