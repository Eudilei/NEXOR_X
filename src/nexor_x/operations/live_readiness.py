from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class LiveReadinessEvaluator:
    """Consolida sinais existentes sem autorizar execução LIVE."""

    _GOOD_STATUS = {
        "OK",
        "READY",
        "HEALTHY",
        "ONLINE",
        "PAPER_AND_TESTNET_READY",
        "READY_FOR_LONG_RUN_VALIDATION",
        "EVIDENCE_MILESTONE_REACHED",
    }

    def evaluate(
        self,
        *,
        mode: str,
        credentials: dict[str, Any],
        recovery: dict[str, Any],
        supervisor: dict[str, Any],
        integration: dict[str, Any],
        validation: dict[str, Any],
        campaign: dict[str, Any],
        cycle: dict[str, Any],
        runtime: dict[str, Any],
    ) -> dict[str, Any]:
        checks = {
            "safe_mode": str(mode).upper() in {"PAPER", "TESTNET"},
            "credentials_configured": self._credentials_ready(credentials),
            "recovery_ok": self._bool_or_status(recovery, "recovery_ok", "status"),
            "supervisor_testnet_allowed": bool(supervisor.get("testnet_allowed", False)),
            "integration_testnet_ready": bool(integration.get("testnet_ready", False)),
            "validation_testnet_ready": bool(validation.get("testnet_validation_ready", False)),
            "campaign_allows_testnet": bool(campaign.get("testnet_allowed", False)),
            "validation_cycle_present": self._cycle_present(cycle),
            "runtime_live_disabled": not bool(runtime.get("live_enabled", False)),
        }
        blockers = [name for name, ok in checks.items() if not ok]
        candidate_ready = not blockers
        return {
            "status": "CANDIDATE_READY" if candidate_ready else "VALIDATION_IN_PROGRESS",
            "candidate_ready": candidate_ready,
            "live_allowed": False,
            "live_certified": False,
            "checks": checks,
            "blockers": blockers,
            "mode": str(mode).upper(),
            "evaluated_at": datetime.now(UTC).isoformat(),
            "safety_note": (
                "LIVE permanece bloqueado. Este relatório mede prontidão para uma futura "
                "certificação, não autorização de capital real."
            ),
        }

    def _credentials_ready(self, payload: dict[str, Any]) -> bool:
        direct = (
            payload.get("binance_configured"),
            payload.get("binance_ready"),
            payload.get("configured"),
            payload.get("ready"),
        )
        if any(value is True for value in direct):
            return True
        for key in ("binance", "exchange"):
            nested = payload.get(key)
            if isinstance(nested, dict) and any(
                nested.get(name) is True
                for name in ("configured", "ready", "api_key_configured")
            ):
                return True
        return False

    def _bool_or_status(self, payload: dict[str, Any], bool_key: str, status_key: str) -> bool:
        if bool_key in payload:
            return bool(payload.get(bool_key))
        return str(payload.get(status_key, "")).upper() in self._GOOD_STATUS

    @staticmethod
    def _cycle_present(payload: dict[str, Any]) -> bool:
        if not payload:
            return False
        if payload.get("run_id"):
            return True
        if payload.get("days_running") is not None:
            return True
        if payload.get("campaign"):
            return True
        return str(payload.get("status", "")).upper() not in {"", "NOT_RUN", "NEVER_RUN", "PENDING"}
