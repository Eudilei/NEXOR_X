from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class EntryAdmissionController:
    """Decide se uma ação pode aumentar exposição.

    Ações reduce-only de proteção não são bloqueadas por degradação.
    LIVE não é habilitado por este controlador.
    """

    def evaluate(
        self,
        *,
        degradation: dict[str, Any],
        action: str,
        reduce_only: bool = False,
    ) -> dict[str, Any]:
        state = str(degradation.get("state", "NORMAL")).upper()
        degradation_allows = bool(
            degradation.get("new_entries_allowed", state != "BLOCKED")
        )

        protective = bool(reduce_only)
        allowed = protective or degradation_allows

        hard_reasons = list(degradation.get("hard_reasons") or [])
        caution_reasons = list(degradation.get("caution_reasons") or [])

        if protective:
            reason = "PROTECTIVE_REDUCE_ONLY"
        elif allowed and state == "CAUTION":
            reason = "ALLOWED_WITH_CAUTION"
        elif allowed:
            reason = "ALLOWED"
        else:
            reason = "BLOCKED_BY_PERFORMANCE_DEGRADATION"

        return {
            "allowed": allowed,
            "action": str(action).upper(),
            "reduce_only": protective,
            "state": state,
            "reason": reason,
            "hard_reasons": hard_reasons,
            "caution_reasons": caution_reasons,
            "manage_existing_positions": True,
            "live_allowed": False,
            "evaluated_at": datetime.now(UTC).isoformat(),
        }

    def require(
        self,
        *,
        degradation: dict[str, Any],
        action: str,
        reduce_only: bool = False,
    ) -> dict[str, Any]:
        result = self.evaluate(
            degradation=degradation,
            action=action,
            reduce_only=reduce_only,
        )
        if result["allowed"]:
            return result

        reasons = result["hard_reasons"] or ["performance_degradation"]
        raise RuntimeError(
            "New entry blocked by performance degradation: "
            + ", ".join(str(item) for item in reasons)
        )
