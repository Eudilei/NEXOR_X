from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from nexor_x.evidence.models import Evidence


class EdgeDecision(StrEnum):
    LONG_BIAS = "LONG_BIAS"
    SHORT_BIAS = "SHORT_BIAS"
    NO_EDGE = "NO_EDGE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True, slots=True)
class QuantAssessment:
    symbol: str
    decision: EdgeDecision
    raw_edge: float
    evidence_coverage: float
    confidence: float
    calibrated: bool
    execution_allowed: bool
    rationale: tuple[str, ...]
    evidences: tuple[Evidence, ...]
    evaluated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "decision": self.decision.value,
            "raw_edge": self.raw_edge,
            "evidence_coverage": self.evidence_coverage,
            "confidence": self.confidence,
            "calibrated": self.calibrated,
            "execution_allowed": self.execution_allowed,
            "rationale": list(self.rationale),
            "evidences": [item.to_dict() for item in self.evidences],
            "evaluated_at": self.evaluated_at.astimezone(UTC).isoformat(),
        }
