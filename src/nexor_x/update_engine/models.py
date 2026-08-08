from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class UpdateStatus(StrEnum):
    APPLIED = "APPLIED"
    DETECTED = "DETECTED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class UpdateRecord:
    update_id: str
    version: str
    status: UpdateStatus
    source: str
    applied_at: datetime
    commit_sha: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["applied_at"] = self.applied_at.isoformat()
        return data
