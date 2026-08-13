
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class UnifiedEntryDecisionTrace:
    def build(
        self,
        *,
        degradation: dict[str, Any],
        recovery: dict[str, Any],
        probation: dict[str, Any],
        exposure: dict[str, Any],
        reservation: dict[str, Any],
    ) -> dict[str, Any]:
        blockers: list[str] = []
        warnings: list[str] = []

        state = str(degradation.get("state", "NORMAL")).upper()

        if state == "BLOCKED":
            blockers.extend(
                str(x) for x in degradation.get("hard_reasons") or []
            )
            if not blockers:
                blockers.append("performance_degradation_blocked")
        elif state == "CAUTION":
            warnings.extend(
                str(x) for x in degradation.get("caution_reasons") or []
            )
            if not warnings:
                warnings.append("performance_degradation_caution")

        if bool(recovery.get("latched", False)):
            blockers.append("recovery_hysteresis_active")

        if bool(probation.get("active", False)):
            warnings.append("post_recovery_probation_active")

        if bool(reservation.get("active", False)):
            blockers.append("entry_reservation_active")

        blockers = list(dict.fromkeys(blockers))
        warnings = list(dict.fromkeys(warnings))

        allowed = (
            not blockers
            and bool(degradation.get("new_entries_allowed", True))
        )

        multiplier = float(exposure.get("exposure_multiplier", 1.0))

        return {
            "status": "ENTRY_ALLOWED" if allowed else "ENTRY_BLOCKED",
            "new_entries_allowed": allowed,
            "blockers": blockers,
            "warnings": warnings,
            "exposure_multiplier": multiplier,
            "exposure_percent": round(multiplier * 100.0, 2),
            "degradation": {
                "state": state,
                "metrics": degradation.get("metrics", {}),
                "hard_reasons": degradation.get("hard_reasons", []),
                "caution_reasons": degradation.get("caution_reasons", []),
            },
            "recovery_hysteresis": recovery,
            "post_recovery_probation": probation,
            "exposure_ramp": exposure,
            "entry_reservation": reservation,
            "read_only": True,
            "live_allowed": False,
            "evaluated_at": datetime.now(UTC).isoformat(),
        }
