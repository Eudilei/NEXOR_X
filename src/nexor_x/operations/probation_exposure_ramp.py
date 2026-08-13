
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class ProbationExposureRampPolicy:
    first_multiplier: float = 0.25
    second_multiplier: float = 0.50
    third_multiplier: float = 0.75
    normal_multiplier: float = 1.00

class ProbationExposureRamp:
    def __init__(self, policy: ProbationExposureRampPolicy | None = None) -> None:
        self.policy = policy or ProbationExposureRampPolicy()

    def multiplier(self, *, probation: dict[str, Any], reduce_only: bool = False) -> float:
        if reduce_only:
            return 1.0
        if not bool(probation.get("active", False)):
            return self.policy.normal_multiplier
        admitted = int(probation.get("admitted_entries", 0))
        if admitted <= 0:
            return self.policy.first_multiplier
        if admitted == 1:
            return self.policy.second_multiplier
        return self.policy.third_multiplier

    def evaluate(self, *, probation: dict[str, Any], reduce_only: bool = False) -> dict[str, Any]:
        mult = self.multiplier(probation=probation, reduce_only=reduce_only)
        return {
            "active": bool(probation.get("active", False)),
            "admitted_entries": int(probation.get("admitted_entries", 0)),
            "reduce_only": bool(reduce_only),
            "exposure_multiplier": mult,
            "exposure_percent": round(mult * 100.0, 2),
            "live_allowed": False,
        }

    @staticmethod
    def scale_quantity(quantity: Any, multiplier: float) -> float:
        value = float(quantity)
        if value <= 0:
            raise ValueError("quantity must be greater than zero")
        if not 0.0 < float(multiplier) <= 1.0:
            raise ValueError("multiplier must be > 0 and <= 1")
        return value * float(multiplier)
