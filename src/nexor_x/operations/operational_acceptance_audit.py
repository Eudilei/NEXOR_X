from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class OperationalAcceptanceAudit:
    """Audita coerência entre gates operacionais sem alterar estado."""

    def run(
        self,
        *,
        readiness: dict[str, Any],
        certification: dict[str, Any],
        degradation: dict[str, Any],
        entry_trace: dict[str, Any],
        summary: dict[str, Any],
    ) -> dict[str, Any]:
        checks: dict[str, bool] = {}

        checks["live_blocked_readiness"] = (
            readiness.get("live_allowed") is False
        )
        checks["live_blocked_certification"] = (
            certification.get("live_allowed") is False
        )
        checks["live_blocked_entry_trace"] = (
            entry_trace.get("live_allowed") is False
        )
        checks["live_blocked_summary"] = (
            summary.get("live_allowed") is False
        )
        checks["live_not_certified"] = (
            summary.get("live_certified") is False
        )

        checks["entry_trace_read_only"] = (
            entry_trace.get("read_only") is True
        )
        checks["summary_read_only"] = (
            summary.get("read_only") is True
        )

        multiplier = self._number(
            summary.get("exposure_multiplier", 1.0),
            default=-1.0,
        )
        checks["exposure_multiplier_valid"] = (
            0.0 < multiplier <= 1.0
        )

        degradation_state = str(
            degradation.get("state", "NORMAL")
        ).upper()

        if degradation_state == "BLOCKED":
            checks["blocked_degradation_blocks_entry"] = (
                entry_trace.get("new_entries_allowed") is False
            )
            checks["blocked_degradation_blocks_summary"] = (
                summary.get("paper_testnet_new_entries_allowed") is False
            )
        else:
            checks["blocked_degradation_blocks_entry"] = True
            checks["blocked_degradation_blocks_summary"] = True

        entry_blockers = set(
            str(item)
            for item in entry_trace.get("blockers") or []
        )
        summary_blockers = set(
            str(item)
            for item in summary.get("blockers") or []
        )
        checks["entry_blockers_propagated_to_summary"] = (
            entry_blockers.issubset(summary_blockers)
        )

        entry_allowed = bool(
            entry_trace.get("new_entries_allowed", False)
        )
        summary_allowed = bool(
            summary.get("paper_testnet_new_entries_allowed", False)
        )
        checks["entry_and_summary_agree"] = (
            entry_allowed == summary_allowed
        )

        candidate_ready = bool(
            readiness.get("candidate_ready", False)
        )
        evidence_certified = bool(
            certification.get("evidence_certified", False)
        )

        if evidence_certified:
            checks["certification_requires_readiness"] = candidate_ready
        else:
            checks["certification_requires_readiness"] = True

        failed = [
            name
            for name, passed in checks.items()
            if not passed
        ]

        return {
            "status": "PASS" if not failed else "FAIL",
            "passed": not failed,
            "checks": checks,
            "failed_checks": failed,
            "check_count": len(checks),
            "passed_check_count": sum(
                1 for passed in checks.values() if passed
            ),
            "candidate_ready": candidate_ready,
            "evidence_certified": evidence_certified,
            "paper_testnet_new_entries_allowed": summary_allowed,
            "live_allowed": False,
            "live_certified": False,
            "read_only": True,
            "safety_note": (
                "PASS confirma coerência dos gates atuais para PAPER/TESTNET; "
                "não autoriza execução LIVE."
            ),
            "evaluated_at": datetime.now(UTC).isoformat(),
        }

    @staticmethod
    def _number(value: Any, *, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
