from __future__ import annotations

from datetime import UTC, datetime

from nexor_x.infrastructure.database import DatabaseService

from .calibration import CalibrationEngine
from .models import CalibrationEstimate, LaboratoryReport, OutcomeObservation
from .validator import WalkForwardValidator


class LaboratoryService:
    def __init__(self, database: DatabaseService, minimum_samples: int = 30) -> None:
        self.database = database
        self.calibration = CalibrationEngine(minimum_samples=minimum_samples)
        self.validator = WalkForwardValidator(self.calibration)

    async def observations(self) -> list[OutcomeObservation]:
        rows = await self.database.fetchall(
            """SELECT symbol, decision, raw_edge, regime, realized_r, closed_at
            FROM quant_observations ORDER BY closed_at ASC"""
        )
        return [
            OutcomeObservation(
                symbol=str(row[0]),
                decision=str(row[1]),
                raw_edge=float(row[2]),
                regime=str(row[3]),
                realized_r=float(row[4]),
                closed_at=datetime.fromisoformat(str(row[5])).astimezone(UTC),
            )
            for row in rows
        ]

    async def estimate(
        self, raw_edge: float, decision: str, regime: str
    ) -> CalibrationEstimate:
        return self.calibration.estimate(
            raw_edge,
            await self.observations(),
            decision=decision,
            regime=regime,
        )

    async def report(self) -> LaboratoryReport:
        return self.validator.run(await self.observations())

    async def status(self) -> dict[str, object]:
        observations = await self.observations()
        report = self.validator.run(observations)
        return {
            "observation_count": len(observations),
            "minimum_samples_per_context": self.calibration.minimum_samples,
            "walk_forward": report.to_dict(),
            "execution_allowed": False,
            "live_certified": False,
        }
