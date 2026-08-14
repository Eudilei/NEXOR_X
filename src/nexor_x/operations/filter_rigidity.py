
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from threading import RLock
from typing import Any


@dataclass(frozen=True)
class FilterRigidityPolicy:
    min_samples: int = 50
    caution_approval_rate: float = 0.08
    severe_approval_rate: float = 0.03


class FilterRigidityMonitor:
    VALID_GROUPS = {"CRITICAL", "SCORE", "REGIME"}

    def __init__(
        self,
        *,
        state_path: str | Path | None = None,
        policy: FilterRigidityPolicy | None = None,
    ) -> None:
        self.state_path = Path(state_path) if state_path else None
        self.policy = policy or FilterRigidityPolicy()
        self._lock = RLock()
        self._state: dict[str, Any] = {
            "evaluated": 0,
            "approved": 0,
            "rejected": 0,
            "filter_rejections": {},
            "group_rejections": {},
        }
        self._load()

    def record(
        self,
        *,
        approved: bool,
        reasons: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        reasons = reasons or []
        with self._lock:
            self._state["evaluated"] += 1
            if approved:
                self._state["approved"] += 1
            else:
                self._state["rejected"] += 1

            fc = Counter(self._state.get("filter_rejections") or {})
            gc = Counter(self._state.get("group_rejections") or {})

            if not approved:
                for item in reasons:
                    name = str(item.get("name", "unknown")).strip() or "unknown"
                    group = str(item.get("group", "SCORE")).upper()
                    if group not in self.VALID_GROUPS:
                        group = "SCORE"
                    fc[name] += 1
                    gc[group] += 1

            self._state["filter_rejections"] = dict(fc)
            self._state["group_rejections"] = dict(gc)
            self._save()
            return self.status()

    def status(self) -> dict[str, Any]:
        with self._lock:
            evaluated = int(self._state["evaluated"])
            approved = int(self._state["approved"])
            rejected = int(self._state["rejected"])
            approval_rate = approved / evaluated if evaluated else 0.0

            if evaluated < self.policy.min_samples:
                status = "LEARNING"
            elif approval_rate < self.policy.severe_approval_rate:
                status = "TOO_RIGID"
            elif approval_rate < self.policy.caution_approval_rate:
                status = "CAUTION"
            else:
                status = "HEALTHY"

            top = sorted(
                (self._state.get("filter_rejections") or {}).items(),
                key=lambda item: item[1],
                reverse=True,
            )[:10]

            return {
                "status": status,
                "evaluated": evaluated,
                "approved": approved,
                "rejected": rejected,
                "approval_rate": round(approval_rate, 6),
                "approval_percent": round(approval_rate * 100.0, 2),
                "filter_rejections": dict(self._state.get("filter_rejections") or {}),
                "group_rejections": dict(self._state.get("group_rejections") or {}),
                "top_rejecting_filters": [
                    {"name": name, "count": count}
                    for name, count in top
                ],
                "critical_filters_auto_relaxed": False,
                "live_allowed": False,
                "read_only": True,
                "evaluated_at": datetime.now(UTC).isoformat(),
            }

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
