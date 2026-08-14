
from __future__ import annotations

from typing import Any


class FilterDecisionTelemetry:
    CRITICAL_TOKENS = (
        "degradation",
        "drawdown",
        "spread",
        "slippage",
        "risk",
        "reservation",
        "recovery",
        "hard_stop",
        "hard-stop",
        "rr_",
        "r:r",
        "operational",
        "latency",
        "blocked",
    )

    REGIME_TOKENS = (
        "regime",
        "trend",
        "context",
        "volatility",
        "mtf",
        "sideways",
        "range",
    )

    def classify(self, reason: str) -> str:
        value = reason.strip().lower()
        if any(token in value for token in self.CRITICAL_TOKENS):
            return "CRITICAL"
        if any(token in value for token in self.REGIME_TOKENS):
            return "REGIME"
        return "SCORE"

    def reasons_from_trace(
        self,
        trace: dict[str, Any],
    ) -> list[dict[str, str]]:
        reasons = [
            {
                "name": str(raw),
                "group": self.classify(str(raw)),
            }
            for raw in (trace.get("blockers") or [])
        ]

        if (
            not reasons
            and not bool(trace.get("new_entries_allowed", False))
        ):
            reasons.append({
                "name": "entry_not_allowed_unspecified",
                "group": "CRITICAL",
            })

        return reasons

    def record_trace(
        self,
        *,
        monitor: Any,
        trace: dict[str, Any],
    ) -> dict[str, Any]:
        return monitor.record(
            approved=bool(
                trace.get("new_entries_allowed", False)
            ),
            reasons=self.reasons_from_trace(trace),
        )
