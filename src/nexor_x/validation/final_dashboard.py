from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class FinalTechnicalDashboardSnapshot:
    """Snapshot read-only para o Command Center."""

    def build(
        self,
        *,
        completion: dict[str, Any],
        campaign: dict[str, Any],
        acceptance: dict[str, Any],
        readiness_summary: dict[str, Any],
    ) -> dict[str, Any]:
        pending = list(
            completion.get("pending_requirements") or []
        )
        blockers = list(
            readiness_summary.get("blockers") or []
        )
        warnings = list(
            readiness_summary.get("warnings") or []
        )

        return {
            "status": completion.get(
                "status", "VALIDATION_PENDING"
            ),
            "technically_complete": bool(
                completion.get("technically_complete", False)
            ),
            "paper_testnet_phase_complete": bool(
                completion.get(
                    "paper_testnet_phase_complete",
                    False,
                )
            ),
            "validation_progress_percent": float(
                campaign.get("progress_percent", 0.0)
            ),
            "validation_status": campaign.get(
                "status", "IN_PROGRESS"
            ),
            "validation_passes": int(
                campaign.get("valid_passes", 0)
            ),
            "validation_required_passes": int(
                campaign.get("required_passes", 20)
            ),
            "acceptance_status": acceptance.get(
                "status", "UNKNOWN"
            ),
            "candidate_ready": bool(
                completion.get("candidate_ready", False)
            ),
            "evidence_certified": bool(
                completion.get("evidence_certified", False)
            ),
            "exposure_multiplier": float(
                readiness_summary.get(
                    "exposure_multiplier",
                    1.0,
                )
            ),
            "pending_requirements": pending,
            "blockers": blockers,
            "warnings": warnings,
            "live_allowed": False,
            "live_certified": False,
            "live_label": "BLOQUEADO",
            "read_only": True,
            "evaluated_at": datetime.now(UTC).isoformat(),
        }
