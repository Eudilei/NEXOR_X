from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FinalValidationCampaignPolicy:
    required_passes: int = 20
    minimum_interval_seconds: int = 30 * 60
    minimum_campaign_seconds: int = 24 * 60 * 60


class FinalValidationCampaignController:
    """Campanha persistente de validação operacional final."""

    def __init__(
        self,
        *,
        state_path: str | Path | None = None,
        policy: FinalValidationCampaignPolicy | None = None,
    ) -> None:
        self.policy = policy or FinalValidationCampaignPolicy()
        self.state_path = Path(state_path) if state_path else None
        self._state: dict[str, Any] = {
            "started_at": None,
            "last_valid_sample_at": None,
            "valid_passes": 0,
            "consecutive_passes": 0,
            "failures": 0,
            "last_audit_status": None,
            "last_failed_checks": [],
        }
        self._load()

    def record(
        self,
        *,
        audit: dict[str, Any],
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = self._utc(now)

        if not self._interval_elapsed(now):
            report = self.status(now=now)
            report["sample_counted"] = False
            report["sample_reason"] = "MINIMUM_INTERVAL_NOT_ELAPSED"
            return report

        status = str(audit.get("status", "FAIL")).upper()
        if self._state["started_at"] is None:
            self._state["started_at"] = now.isoformat()

        self._state["last_valid_sample_at"] = now.isoformat()
        self._state["last_audit_status"] = status

        if status == "PASS" and bool(audit.get("passed", False)):
            self._state["valid_passes"] = int(
                self._state["valid_passes"]
            ) + 1
            self._state["consecutive_passes"] = int(
                self._state["consecutive_passes"]
            ) + 1
            self._state["last_failed_checks"] = []
            sample_reason = "PASS_RECORDED"
        else:
            self._state["failures"] = int(
                self._state["failures"]
            ) + 1
            self._state["consecutive_passes"] = 0
            self._state["last_failed_checks"] = list(
                audit.get("failed_checks") or []
            )
            sample_reason = "FAIL_RECORDED"

        self._save()

        report = self.status(now=now)
        report["sample_counted"] = True
        report["sample_reason"] = sample_reason
        return report

    def status(
        self,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = self._utc(now)

        elapsed = self._elapsed_seconds(now)
        pass_count = int(self._state["valid_passes"])
        consecutive = int(self._state["consecutive_passes"])

        enough_passes = pass_count >= self.policy.required_passes
        enough_time = elapsed >= self.policy.minimum_campaign_seconds

        completed = enough_passes and enough_time
        progress = min(
            100.0,
            (
                pass_count / self.policy.required_passes * 100.0
                if self.policy.required_passes > 0
                else 100.0
            ),
        )

        return {
            "status": "COMPLETE" if completed else "IN_PROGRESS",
            "completed": completed,
            "valid_passes": pass_count,
            "consecutive_passes": consecutive,
            "failures": int(self._state["failures"]),
            "required_passes": self.policy.required_passes,
            "minimum_interval_seconds": (
                self.policy.minimum_interval_seconds
            ),
            "minimum_campaign_seconds": (
                self.policy.minimum_campaign_seconds
            ),
            "elapsed_seconds": elapsed,
            "progress_percent": round(progress, 2),
            "started_at": self._state.get("started_at"),
            "last_valid_sample_at": self._state.get(
                "last_valid_sample_at"
            ),
            "last_audit_status": self._state.get(
                "last_audit_status"
            ),
            "last_failed_checks": list(
                self._state.get("last_failed_checks") or []
            ),
            "evidence_certification_still_required": True,
            "live_allowed": False,
            "live_certified": False,
            "read_only": True,
            "evaluated_at": now.isoformat(),
        }

    def _interval_elapsed(self, now: datetime) -> bool:
        last = self._parse_dt(
            self._state.get("last_valid_sample_at")
        )
        if last is None:
            return True
        return (
            now - last
        ).total_seconds() >= self.policy.minimum_interval_seconds

    def _elapsed_seconds(self, now: datetime) -> float:
        started = self._parse_dt(self._state.get("started_at"))
        if started is None:
            return 0.0
        return max(0.0, (now - started).total_seconds())

    def _load(self) -> None:
        if self.state_path is None or not self.state_path.exists():
            return
        try:
            payload = json.loads(
                self.state_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(payload, dict):
            for key in self._state:
                if key in payload:
                    self._state[key] = payload[key]

    def _save(self) -> None:
        if self.state_path is None:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(
            self.state_path.suffix + ".tmp"
        )
        tmp.write_text(
            json.dumps(
                self._state,
                indent=2,
                ensure_ascii=False,
            ) + "\n",
            encoding="utf-8",
        )
        tmp.replace(self.state_path)

    @staticmethod
    def _parse_dt(value: Any) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    @staticmethod
    def _utc(value: datetime | None) -> datetime:
        if value is None:
            return datetime.now(UTC)
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
