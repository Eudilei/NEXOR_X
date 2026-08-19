from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RecoveryHysteresisPolicy:
    cooldown_seconds: int = 15 * 60
    required_healthy_checks: int = 3
    min_healthy_check_interval_seconds: int = 5 * 60


class RecoveryHysteresisController:
    """Mantém bloqueio após degradação até recuperação confirmada."""

    def __init__(
        self,
        *,
        state_path: str | Path | None = None,
        policy: RecoveryHysteresisPolicy | None = None,
    ) -> None:
        self.policy = policy or RecoveryHysteresisPolicy()
        self.state_path = Path(state_path) if state_path else None
        self._state: dict[str, Any] = {
            "latched": False,
            "blocked_since": None,
            "healthy_checks": 0,
            "last_healthy_check_at": None,
        }
        self._load()

    def evaluate(
        self,
        *,
        degradation: dict[str, Any],
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = self._utc(now)
        raw_state = str(degradation.get("state", "NORMAL")).upper()
        was_latched = bool(self._state["latched"])
        transition: str | None = None

        if raw_state == "BLOCKED":
            if not was_latched:
                transition = "LATCHED"
            self._state["latched"] = True
            if not self._state.get("blocked_since"):
                self._state["blocked_since"] = now.isoformat()
            self._state["healthy_checks"] = 0
            self._state["last_healthy_check_at"] = None

        elif self._state["latched"]:
            recovery_reasons = set(degradation.get("recovery_reasons") or [])
            caution_reasons = set(degradation.get("caution_reasons") or [])
            healthy_for_recovery = bool(
                raw_state == "NORMAL"
                or (
                    raw_state == "CAUTION"
                    and "shadow_recovery_confirmed" in recovery_reasons
                    and caution_reasons.issubset({"evidence_not_certified"})
                )
            )
            if healthy_for_recovery:
                if self._can_count_healthy_check(now):
                    self._state["healthy_checks"] = (
                        int(self._state.get("healthy_checks", 0)) + 1
                    )
                    self._state["last_healthy_check_at"] = now.isoformat()
            else:
                self._state["healthy_checks"] = 0
                self._state["last_healthy_check_at"] = None

            if self._recovery_requirements_met(now):
                self._state = {
                    "latched": False,
                    "blocked_since": None,
                    "healthy_checks": 0,
                    "last_healthy_check_at": None,
                }
                transition = "RECOVERED"

        self._save()

        latched = bool(self._state["latched"])
        effective = dict(degradation)

        if latched:
            effective["state"] = "BLOCKED"
            effective["new_entries_allowed"] = False
            hard = list(effective.get("hard_reasons") or [])
            if "recovery_hysteresis_active" not in hard:
                hard.append("recovery_hysteresis_active")
            effective["hard_reasons"] = hard

        return {
            "raw_state": raw_state,
            "effective_state": str(effective.get("state", raw_state)).upper(),
            "new_entries_allowed": bool(
                effective.get("new_entries_allowed", False)
            ),
            "latched": latched,
            "healthy_checks": int(self._state.get("healthy_checks", 0)),
            "required_healthy_checks": self.policy.required_healthy_checks,
            "cooldown_seconds": self.policy.cooldown_seconds,
            "elapsed_since_block_seconds": self._elapsed_seconds(now),
            "min_healthy_check_interval_seconds": (
                self.policy.min_healthy_check_interval_seconds
            ),
            "transition": transition,
            "degradation": effective,
            "live_allowed": False,
            "evaluated_at": now.isoformat(),
        }

    def status(
        self,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = self._utc(now)
        return {
            "latched": bool(self._state["latched"]),
            "blocked_since": self._state.get("blocked_since"),
            "healthy_checks": int(self._state.get("healthy_checks", 0)),
            "required_healthy_checks": self.policy.required_healthy_checks,
            "cooldown_seconds": self.policy.cooldown_seconds,
            "elapsed_since_block_seconds": self._elapsed_seconds(now),
            "min_healthy_check_interval_seconds": (
                self.policy.min_healthy_check_interval_seconds
            ),
            "read_only": True,
            "live_allowed": False,
            "evaluated_at": now.isoformat(),
        }

    def _can_count_healthy_check(self, now: datetime) -> bool:
        last = self._parse_dt(self._state.get("last_healthy_check_at"))
        if last is None:
            return True
        return (
            now - last
        ).total_seconds() >= self.policy.min_healthy_check_interval_seconds

    def _recovery_requirements_met(self, now: datetime) -> bool:
        enough_checks = (
            int(self._state.get("healthy_checks", 0))
            >= self.policy.required_healthy_checks
        )
        enough_time = self._elapsed_seconds(now) >= self.policy.cooldown_seconds
        return bool(self._state["latched"]) and enough_checks and enough_time

    def _elapsed_seconds(self, now: datetime) -> float:
        blocked_since = self._parse_dt(self._state.get("blocked_since"))
        if blocked_since is None:
            return 0.0
        return max(0.0, (now - blocked_since).total_seconds())

    def _load(self) -> None:
        if self.state_path is None or not self.state_path.exists():
            return
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
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
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(self._state, indent=2, ensure_ascii=False) + "\n",
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
