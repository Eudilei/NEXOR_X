from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class ScannerCandidate:
    symbol: str
    decision: str
    raw_edge: float
    confidence: float
    calibrated: bool
    expected_r: float | None
    profit_factor: float | None
    calibration_samples: int
    stale: bool
    regime: str
    evaluated_at: datetime

    @property
    def rank_score(self) -> float:
        calibration_bonus = 0.15 if self.calibrated else 0.0
        expected_bonus = max(min(self.expected_r or 0.0, 1.0), -1.0) * 0.20
        pf_bonus = max(min((self.profit_factor or 0.0) - 1.0, 1.0), -1.0) * 0.10
        stale_penalty = 0.30 if self.stale else 0.0
        directional_edge = abs(self.raw_edge)
        return round(
            directional_edge * 0.55
            + self.confidence * 0.20
            + calibration_bonus
            + expected_bonus
            + pf_bonus
            - stale_penalty,
            6,
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evaluated_at"] = self.evaluated_at.astimezone(UTC).isoformat()
        data["rank_score"] = self.rank_score
        return data


@dataclass(frozen=True, slots=True)
class ScannerRun:
    run_id: str
    started_at: datetime
    finished_at: datetime
    symbols_requested: int
    symbols_succeeded: int
    symbols_failed: int
    candidates: tuple[ScannerCandidate, ...]
    errors: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.astimezone(UTC).isoformat(),
            "finished_at": self.finished_at.astimezone(UTC).isoformat(),
            "duration_seconds": round((self.finished_at - self.started_at).total_seconds(), 4),
            "symbols_requested": self.symbols_requested,
            "symbols_succeeded": self.symbols_succeeded,
            "symbols_failed": self.symbols_failed,
            "candidates": [item.to_dict() for item in self.candidates],
            "errors": list(self.errors),
            "execution_triggered": False,
        }
