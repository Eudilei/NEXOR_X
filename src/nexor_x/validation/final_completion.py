from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class FinalTechnicalCompletionGate:
    """Gate final da fase técnica PAPER/TESTNET."""

    def evaluate(
        self,
        *,
        acceptance_audit: dict[str, Any],
        campaign: dict[str, Any],
        readiness: dict[str, Any],
        certification: dict[str, Any],
    ) -> dict[str, Any]:
        requirements = {
            "acceptance_audit_passed": (
                acceptance_audit.get("status") == "PASS"
                and acceptance_audit.get("passed") is True
            ),
            "validation_campaign_complete": (
                campaign.get("status") == "COMPLETE"
                and campaign.get("completed") is True
            ),
            "candidate_ready": bool(
                readiness.get("candidate_ready", False)
            ),
            "evidence_certified": bool(
                certification.get("evidence_certified", False)
            ),
            "live_still_blocked": (
                acceptance_audit.get("live_allowed") is False
                and campaign.get("live_allowed") is False
                and readiness.get("live_allowed") is False
                and certification.get("live_allowed") is False
            ),
        }

        pending = [
            name
            for name, passed in requirements.items()
            if not passed
        ]

        if not requirements["acceptance_audit_passed"]:
            status = "BLOCKED"
        elif not requirements["validation_campaign_complete"]:
            status = "VALIDATION_PENDING"
        elif (
            not requirements["candidate_ready"]
            or not requirements["evidence_certified"]
        ):
            status = "EVIDENCE_PENDING"
        elif not requirements["live_still_blocked"]:
            status = "BLOCKED"
        else:
            status = "TECHNICALLY_COMPLETE"

        technically_complete = status == "TECHNICALLY_COMPLETE"

        return {
            "status": status,
            "technically_complete": technically_complete,
            "requirements": requirements,
            "pending_requirements": pending,
            "acceptance_audit_status": acceptance_audit.get(
                "status", "UNKNOWN"
            ),
            "validation_campaign_status": campaign.get(
                "status", "UNKNOWN"
            ),
            "validation_progress_percent": float(
                campaign.get("progress_percent", 0.0)
            ),
            "candidate_ready": requirements["candidate_ready"],
            "evidence_certified": requirements["evidence_certified"],
            "paper_testnet_phase_complete": technically_complete,
            "live_allowed": False,
            "live_certified": False,
            "read_only": True,
            "safety_note": (
                "TECHNICALLY_COMPLETE encerra somente a fase técnica "
                "PAPER/TESTNET. Não concede autorização LIVE."
            ),
            "evaluated_at": datetime.now(UTC).isoformat(),
        }
