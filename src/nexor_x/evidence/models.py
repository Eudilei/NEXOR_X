from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class EvidenceDirection(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True, slots=True)
class Evidence:
    name: str
    direction: EvidenceDirection
    strength: float
    reliability: float
    rationale: str
    source_fields: tuple[str, ...]

    @property
    def signed_value(self) -> float:
        sign = 1.0 if self.direction is EvidenceDirection.BULLISH else -1.0 if self.direction is EvidenceDirection.BEARISH else 0.0
        return round(sign * self.strength * self.reliability, 6)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["direction"] = self.direction.value
        data["signed_value"] = self.signed_value
        data["source_fields"] = list(self.source_fields)
        return data
