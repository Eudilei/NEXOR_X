
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class UnifiedOperationalReadinessSummary:
    def build(
        self,
        *,
        readiness: dict[str, Any],
        certification: dict[str, Any],
        degradation: dict[str, Any],
        entry_trace: dict[str, Any],
    ) -> dict[str, Any]:
        blockers: list[str] = []
        warnings: list[str] = []

        blockers.extend(str(x) for x in readiness.get("blockers") or [])
        blockers.extend(str(x) for x in certification.get("blockers") or [])
        blockers.extend(str(x) for x in entry_trace.get("blockers") or [])

        warnings.extend(str(x) for x in entry_trace.get("warnings") or [])
        warnings.extend(str(x) for x in degradation.get("caution_reasons") or [])

        state = str(degradation.get("state", "NORMAL")).upper()

        if state == "BLOCKED":
            reasons = list(degradation.get("hard_reasons") or [])
            blockers.extend(str(x) for x in reasons)
            if not reasons:
                blockers.append("performance_degradation_blocked")
        elif state == "CAUTION":
            warnings.append("performance_degradation_caution")

        blockers = list(dict.fromkeys(blockers))
        warnings = list(dict.fromkeys(warnings))

        paper_testnet_allowed = (
            bool(entry_trace.get("new_entries_allowed", False))
            and state != "BLOCKED"
        )

        if blockers:
            overall_status = "BLOCKED"
        elif warnings:
            overall_status = "CAUTION"
        elif paper_testnet_allowed:
            overall_status = "READY"
        else:
            overall_status = "VALIDATION_IN_PROGRESS"

        return {
            "overall_status": overall_status,
            "paper_testnet_new_entries_allowed": paper_testnet_allowed,
            "candidate_ready": bool(readiness.get("candidate_ready", False)),
            "evidence_certified": bool(
                certification.get("evidence_certified", False)
            ),
            "performance_state": state,
            "entry_status": entry_trace.get("status", "UNKNOWN"),
            "exposure_multiplier": float(
                entry_trace.get("exposure_multiplier", 1.0)
            ),
            "blockers": blockers,
            "warnings": warnings,
            "readiness": readiness,
            "certification": certification,
            "degradation": degradation,
            "entry_trace": entry_trace,
            "live_allowed": False,
            "live_certified": False,
            "read_only": True,
            "evaluated_at": datetime.now(UTC).isoformat(),
        }
