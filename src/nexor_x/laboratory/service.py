from __future__ import annotations

from datetime import UTC, datetime

from nexor_x.infrastructure.database import DatabaseService

from .calibration import CalibrationEngine
from .models import CalibrationEstimate, LaboratoryReport, OutcomeObservation
from .probability import ProbabilityCalibrationEngine, ProbabilityCalibrationReport
from .edge_discovery import EdgeDiscoveryEngine
from .validator import WalkForwardValidator
from .monte_carlo import MonteCarloConfig, MonteCarloEngine
from .walk_forward import ContinuousWalkForwardEngine, WalkForwardConfig
from .counterfactual import CounterfactualConfig, CounterfactualEngine


class LaboratoryService:
    def __init__(
        self, database: DatabaseService, minimum_samples: int = 30,
        minimum_expected_r: float = 0.05, minimum_profit_factor: float = 1.10,
        maximum_fdr: float = 0.10, probability_minimum_samples: int = 60,
        probability_holdout_fraction: float = 0.25, probability_kelly_fraction: float = 0.25,
        monte_carlo_minimum_observations: int = 60,
    ) -> None:
        self.database = database
        self.calibration = CalibrationEngine(minimum_samples=minimum_samples)
        self.validator = WalkForwardValidator(self.calibration)
        self.probability = ProbabilityCalibrationEngine(
            minimum_samples=probability_minimum_samples,
            holdout_fraction=probability_holdout_fraction,
            kelly_fraction=probability_kelly_fraction,
        )
        self.monte_carlo = MonteCarloEngine(database, minimum_observations=monte_carlo_minimum_observations)
        self.walk_forward_engine = ContinuousWalkForwardEngine(database, self.calibration)
        self.counterfactual = CounterfactualEngine(database)
        self.edge_discovery = EdgeDiscoveryEngine(
            database, minimum_samples=minimum_samples,
            minimum_expected_r=minimum_expected_r,
            minimum_profit_factor=minimum_profit_factor, maximum_fdr=maximum_fdr,
        )

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


    async def probability_estimate(
        self, raw_edge: float, decision: str, regime: str
    ) -> ProbabilityCalibrationReport:
        return self.probability.calibrate(
            raw_edge, await self.observations(), decision=decision, regime=regime
        )

    async def report(self) -> LaboratoryReport:
        return self.validator.run(await self.observations())

    async def discover_edges(self) -> dict[str, object]:
        return await self.edge_discovery.discover(await self.observations())


    async def run_monte_carlo(
        self, config: MonteCarloConfig, *, symbol: str | None = None,
        decision: str | None = None, regime: str | None = None,
    ) -> dict[str, object]:
        report = await self.monte_carlo.run(
            await self.observations(), config, symbol=symbol, decision=decision, regime=regime
        )
        return report.to_dict()

    async def monte_carlo_status(self) -> dict[str, object]:
        return await self.monte_carlo.latest()


    async def run_walk_forward(
        self, config: WalkForwardConfig, *, symbol: str | None = None,
        decision: str | None = None, regime: str | None = None,
    ) -> dict[str, object]:
        report = await self.walk_forward_engine.run(
            await self.observations(), config, symbol=symbol, decision=decision, regime=regime
        )
        return report.to_dict()

    async def walk_forward_status(self) -> dict[str, object]:
        return await self.walk_forward_engine.latest()

    async def run_counterfactual(
        self, config: CounterfactualConfig, *, symbol: str | None = None,
        decision: str | None = None, regime: str | None = None,
    ) -> dict[str, object]:
        report = await self.counterfactual.run(
            await self.observations(), config, symbol=symbol, decision=decision, regime=regime
        )
        return report.to_dict()

    async def counterfactual_status(self) -> dict[str, object]:
        return await self.counterfactual.latest()

    async def edge_status(self) -> dict[str, object]:
        return await self.edge_discovery.latest()

    async def status(self) -> dict[str, object]:
        observations = await self.observations()
        report = self.validator.run(observations)
        return {
            "observation_count": len(observations),
            "minimum_samples_per_context": self.calibration.minimum_samples,
            "probability_minimum_samples": self.probability.minimum_samples,
            "walk_forward": report.to_dict(),
            "execution_allowed": False,
            "live_certified": False,
        }
