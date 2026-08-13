
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import threading
import uuid
from typing import Any


@dataclass(frozen=True)
class EntryReservationPolicy:
    reservation_ttl_seconds: int = 30


class _EntryReservationTransaction:
    def __init__(
        self,
        guard: "AtomicEntryReservationGuard",
        *,
        action: str,
        metadata: dict[str, Any] | None,
        bypass: bool,
    ) -> None:
        self.guard = guard
        self.action = action
        self.metadata = metadata
        self.bypass = bypass
        self.reservation_id: str | None = None

    def __enter__(self) -> dict[str, Any]:
        if self.bypass:
            return {
                "allowed": True,
                "reason": "BYPASS_REDUCE_ONLY",
                "active": False,
                "reservation_id": None,
                "bypass": True,
                "live_allowed": False,
            }

        result = self.guard.reserve(
            action=self.action,
            metadata=self.metadata,
        )
        if not result["allowed"]:
            raise RuntimeError(
                "New entry blocked by active atomic reservation: "
                + str(result.get("reservation_id") or "active")
            )

        self.reservation_id = str(result["reservation_id"])
        result["bypass"] = False
        return result

    def __exit__(self, exc_type, exc, tb) -> bool:
        if self.bypass or self.reservation_id is None:
            return False

        if exc_type is None:
            self.guard.confirm(self.reservation_id)
        else:
            self.guard.release(self.reservation_id)

        return False


class AtomicEntryReservationGuard:
    """Reserva atômica para serializar novas admissões."""

    def __init__(
        self,
        *,
        state_path: str | Path | None = None,
        policy: EntryReservationPolicy | None = None,
    ) -> None:
        self.policy = policy or EntryReservationPolicy()
        self.state_path = Path(state_path) if state_path else None
        self._lock = threading.RLock()
        self._state: dict[str, Any] = {
            "reservation_id": None,
            "action": None,
            "created_at": None,
            "expires_at": None,
            "metadata": {},
        }
        self._load()

    def transaction(
        self,
        *,
        action: str,
        metadata: dict[str, Any] | None = None,
        bypass: bool = False,
    ) -> _EntryReservationTransaction:
        return _EntryReservationTransaction(
            self,
            action=action,
            metadata=metadata,
            bypass=bypass,
        )

    def reserve(
        self,
        *,
        action: str,
        metadata: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = self._utc(now)
        with self._lock:
            self._expire_if_needed(now)

            if self._state.get("reservation_id"):
                return self._report(
                    False,
                    "ENTRY_RESERVATION_ALREADY_ACTIVE",
                    now,
                )

            reservation_id = uuid.uuid4().hex
            expires_at = datetime.fromtimestamp(
                now.timestamp() + self.policy.reservation_ttl_seconds,
                tz=UTC,
            )

            self._state = {
                "reservation_id": reservation_id,
                "action": str(action).upper(),
                "created_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "metadata": dict(metadata or {}),
            }
            self._save()
            return self._report(True, "RESERVED", now)

    def confirm(
        self,
        reservation_id: str,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = self._utc(now)
        with self._lock:
            self._expire_if_needed(now)

            if self._state.get("reservation_id") != reservation_id:
                return self._report(False, "RESERVATION_NOT_FOUND", now)

            snapshot = dict(self._state)
            self._clear()

            return {
                "confirmed": True,
                "reason": "CONFIRMED",
                "reservation": snapshot,
                "active": False,
                "live_allowed": False,
                "evaluated_at": now.isoformat(),
            }

    def release(
        self,
        reservation_id: str,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = self._utc(now)
        with self._lock:
            self._expire_if_needed(now)

            if self._state.get("reservation_id") != reservation_id:
                return self._report(False, "RESERVATION_NOT_FOUND", now)

            self._clear()
            return {
                "released": True,
                "reason": "RELEASED",
                "active": False,
                "live_allowed": False,
                "evaluated_at": now.isoformat(),
            }

    def status(self, *, now: datetime | None = None) -> dict[str, Any]:
        now = self._utc(now)
        with self._lock:
            self._expire_if_needed(now)
            active = bool(self._state.get("reservation_id"))
            return self._report(
                not active,
                (
                    "ENTRY_RESERVATION_ALREADY_ACTIVE"
                    if active
                    else "AVAILABLE"
                ),
                now,
            )

    def _report(
        self,
        allowed: bool,
        reason: str,
        now: datetime,
    ) -> dict[str, Any]:
        return {
            "allowed": allowed,
            "reason": reason,
            "active": bool(self._state.get("reservation_id")),
            "reservation_id": self._state.get("reservation_id"),
            "action": self._state.get("action"),
            "created_at": self._state.get("created_at"),
            "expires_at": self._state.get("expires_at"),
            "ttl_seconds": self.policy.reservation_ttl_seconds,
            "metadata": dict(self._state.get("metadata") or {}),
            "live_allowed": False,
            "evaluated_at": now.isoformat(),
        }

    def _expire_if_needed(self, now: datetime) -> None:
        expires = self._parse_dt(self._state.get("expires_at"))
        if expires is not None and now >= expires:
            self._clear()

    def _clear(self) -> None:
        self._state = {
            "reservation_id": None,
            "action": None,
            "created_at": None,
            "expires_at": None,
            "metadata": {},
        }
        self._save()

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
