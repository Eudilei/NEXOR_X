from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class ReleaseCandidateAudit:
    """Auditoria final da arquitetura antes do congelamento."""

    REQUIRED_COMPONENTS = (
        "live_readiness",
        "live_certification",
        "performance_degradation",
        "recovery_hysteresis",
        "entry_admission",
        "post_recovery_probation",
        "exposure_ramp",
        "entry_reservation",
        "entry_decision_trace",
        "operational_readiness_summary",
        "operational_acceptance_audit",
        "final_validation_campaign",
        "final_technical_completion",
        "final_dashboard_snapshot",
    )

    def evaluate(
        self,
        *,
        acceptance: dict[str, Any],
        final_snapshot: dict[str, Any],
        component_presence: dict[str, bool],
        version: str,
    ) -> dict[str, Any]:
        checks: dict[str, bool] = {}

        checks["acceptance_audit_passed"] = (
            acceptance.get("status") == "PASS"
            and acceptance.get("passed") is True
        )
        checks["acceptance_live_blocked"] = (
            acceptance.get("live_allowed") is False
        )
        checks["snapshot_read_only"] = (
            final_snapshot.get("read_only") is True
        )
        checks["snapshot_live_blocked"] = (
            final_snapshot.get("live_allowed") is False
        )
        checks["snapshot_live_not_certified"] = (
            final_snapshot.get("live_certified") is False
        )

        missing_components = [
            name
            for name in self.REQUIRED_COMPONENTS
            if not bool(component_presence.get(name, False))
        ]
        checks["all_critical_components_present"] = (
            len(missing_components) == 0
        )

        failed_checks = [
            name
            for name, passed in checks.items()
            if not passed
        ]

        rc_ready = not failed_checks

        return {
            "status": "RC_READY" if rc_ready else "RC_BLOCKED",
            "rc_ready": rc_ready,
            "architecture_frozen": rc_ready,
            "version": str(version),
            "checks": checks,
            "failed_checks": failed_checks,
            "missing_components": missing_components,
            "critical_component_count": len(
                self.REQUIRED_COMPONENTS
            ),
            "final_status": final_snapshot.get(
                "status", "UNKNOWN"
            ),
            "validation_progress_percent": float(
                final_snapshot.get(
                    "validation_progress_percent",
                    0.0,
                )
            ),
            "candidate_ready": bool(
                final_snapshot.get("candidate_ready", False)
            ),
            "evidence_certified": bool(
                final_snapshot.get(
                    "evidence_certified",
                    False,
                )
            ),
            "live_allowed": False,
            "live_certified": False,
            "read_only": True,
            "freeze_policy": (
                "Após RC_READY, alterar arquitetura somente para corrigir "
                "bug real, falha de integração ou risco detectado."
            ),
            "safety_note": (
                "RC_READY encerra a construção da arquitetura. "
                "Não autoriza execução LIVE."
            ),
            "evaluated_at": datetime.now(UTC).isoformat(),
        }
