from __future__ import annotations
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

class OperatingMode(StrEnum):
    PAPER = "PAPER"
    LIVE = "LIVE"

class ServiceState(StrEnum):
    STARTING = "STARTING"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"

@dataclass(frozen=True, slots=True)
class Event:
    topic: str
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

@dataclass(slots=True)
class ServiceHealth:
    name: str
    state: ServiceState
    details: str = ""
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(UTC))
    restart_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "details": self.details,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "restart_count": self.restart_count,
        }
