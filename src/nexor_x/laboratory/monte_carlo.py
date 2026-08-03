from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import mean
from typing import Iterable, Sequence

from nexor_x.infrastructure.database import DatabaseService

from .models import OutcomeObservation


@dataclass(frozen=True, slots=True)
class MonteCarloConfig:
    simulations: int = 5000
    horizon_trades: int = 250
    block_size: int = 10
    starting_equity_r: float = 100.0
    ruin_drawdown_pct: float = 25.0
    seed: int = 20260803

    def validate(self) -> None:
        if not 100 <= self.simulations <= 100_000:
            raise ValueError("simulations must be between 100 and 100000")
        if not 20 <= self.horizon_trades <= 100_000:
            raise ValueError("horizon_trades must be between 20 and 100000")
        if not 1 <= self.block_size <= self.horizon_trades:
            raise ValueError("block_size must be between 1 and horizon_trades")
        if self.starting_equity_r <= 0:
            raise ValueError("starting_equity_r must be positive")
        if not 0 < self.ruin_drawdown_pct <= 100:
            raise ValueError("ruin_drawdown_pct must be in (0, 100]")


@dataclass(frozen=True, slots=True)
class MonteCarloReport:
    run_id: str
    generated_at: datetime
    status: str
    observation_count: int
    simulations: int
    horizon_trades: int
    block_size: int
    seed: int
    starting_equity_r: float
    ruin_drawdown_pct: float
    expected_final_equity_r: float | None
    median_final_equity_r: float | None
    final_equity_p05_r: float | None
    final_equity_p95_r: float | None
    median_max_drawdown_pct: float | None
    max_drawdown_p95_pct: float | None
    probability_of_ruin: float | None
    probability_final_below_start: float | None
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "generated_at": self.generated_at.astimezone(UTC).isoformat(),
            "status": self.status,
            "observation_count": self.observation_count,
            "simulations": self.simulations,
            "horizon_trades": self.horizon_trades,
            "block_size": self.block_size,
            "seed": self.seed,
            "starting_equity_r": self.starting_equity_r,
            "ruin_drawdown_pct": self.ruin_drawdown_pct,
            "expected_final_equity_r": self.expected_final_equity_r,
            "median_final_equity_r": self.median_final_equity_r,
            "final_equity_p05_r": self.final_equity_p05_r,
            "final_equity_p95_r": self.final_equity_p95_r,
            "median_max_drawdown_pct": self.median_max_drawdown_pct,
            "max_drawdown_p95_pct": self.max_drawdown_p95_pct,
            "probability_of_ruin": self.probability_of_ruin,
            "probability_final_below_start": self.probability_final_below_start,
            "reason": self.reason,
            "execution_allowed": False,
            "live_certified": False,
        }


class MonteCarloEngine:
    """Moving-block bootstrap over closed-trade R outcomes.

    Blocks preserve short-range streaks better than IID shuffling. The engine is
    a robustness diagnostic only; it never turns historical outcomes into a
    guarantee and never authorizes execution.
    """

    def __init__(self, database: DatabaseService, minimum_observations: int = 60) -> None:
        if minimum_observations < 20:
            raise ValueError("minimum_observations must be at least 20")
        self.database = database
        self.minimum_observations = minimum_observations

    async def run(
        self,
        observations: Iterable[OutcomeObservation],
        config: MonteCarloConfig,
        *,
        symbol: str | None = None,
        decision: str | None = None,
        regime: str | None = None,
    ) -> MonteCarloReport:
        config.validate()
        selected = sorted(
            (
                item
                for item in observations
                if (symbol is None or item.symbol == symbol)
                and (decision is None or item.decision == decision)
                and (regime is None or item.regime == regime)
            ),
            key=lambda item: item.closed_at,
        )
        run_id = str(uuid.uuid4())
        generated_at = datetime.now(UTC)
        if len(selected) < self.minimum_observations:
            report = MonteCarloReport(
                run_id=run_id,
                generated_at=generated_at,
                status="INSUFFICIENT_DATA",
                observation_count=len(selected),
                simulations=config.simulations,
                horizon_trades=config.horizon_trades,
                block_size=config.block_size,
                seed=config.seed,
                starting_equity_r=config.starting_equity_r,
                ruin_drawdown_pct=config.ruin_drawdown_pct,
                expected_final_equity_r=None,
                median_final_equity_r=None,
                final_equity_p05_r=None,
                final_equity_p95_r=None,
                median_max_drawdown_pct=None,
                max_drawdown_p95_pct=None,
                probability_of_ruin=None,
                probability_final_below_start=None,
                reason=(
                    f"amostra insuficiente: {len(selected)}/{self.minimum_observations}; "
                    "nenhuma inferencia de robustez foi emitida"
                ),
            )
            await self._persist(report, symbol, decision, regime)
            return report

        outcomes = [item.realized_r for item in selected]
        rng = random.Random(config.seed)
        finals: list[float] = []
        drawdowns: list[float] = []
        ruined = 0
        below_start = 0
        for _ in range(config.simulations):
            path = self._moving_block_sample(
                outcomes, config.horizon_trades, config.block_size, rng
            )
            equity = config.starting_equity_r
            peak = equity
            max_drawdown = 0.0
            hit_ruin = False
            for realized_r in path:
                equity += realized_r
                peak = max(peak, equity)
                drawdown = (peak - equity) / peak * 100.0 if peak > 0 else 100.0
                max_drawdown = max(max_drawdown, drawdown)
                if drawdown >= config.ruin_drawdown_pct or equity <= 0:
                    hit_ruin = True
            finals.append(equity)
            drawdowns.append(max_drawdown)
            ruined += int(hit_ruin)
            below_start += int(equity < config.starting_equity_r)

        probability_of_ruin = ruined / config.simulations
        p95_drawdown = self._quantile(drawdowns, 0.95)
        status = "ROBUST" if probability_of_ruin <= 0.05 and p95_drawdown < config.ruin_drawdown_pct else "REJECTED"
        report = MonteCarloReport(
            run_id=run_id,
            generated_at=generated_at,
            status=status,
            observation_count=len(selected),
            simulations=config.simulations,
            horizon_trades=config.horizon_trades,
            block_size=config.block_size,
            seed=config.seed,
            starting_equity_r=config.starting_equity_r,
            ruin_drawdown_pct=config.ruin_drawdown_pct,
            expected_final_equity_r=round(mean(finals), 6),
            median_final_equity_r=round(self._quantile(finals, 0.50), 6),
            final_equity_p05_r=round(self._quantile(finals, 0.05), 6),
            final_equity_p95_r=round(self._quantile(finals, 0.95), 6),
            median_max_drawdown_pct=round(self._quantile(drawdowns, 0.50), 6),
            max_drawdown_p95_pct=round(p95_drawdown, 6),
            probability_of_ruin=round(probability_of_ruin, 6),
            probability_final_below_start=round(below_start / config.simulations, 6),
            reason=(
                "moving-block bootstrap concluido; ROBUST exige probabilidade de ruina <= 5% "
                "e drawdown P95 abaixo do limite; resultado nao certifica LIVE"
            ),
        )
        await self._persist(report, symbol, decision, regime)
        return report

    async def latest(self) -> dict[str, object]:
        rows = await self.database.fetchall(
            """SELECT run_id, generated_at, status, observation_count, simulations,
            horizon_trades, block_size, seed, starting_equity_r, ruin_drawdown_pct,
            expected_final_equity_r, median_final_equity_r, final_equity_p05_r,
            final_equity_p95_r, median_max_drawdown_pct, max_drawdown_p95_pct,
            probability_of_ruin, probability_final_below_start, reason,
            symbol, decision, regime
            FROM monte_carlo_runs ORDER BY generated_at DESC LIMIT 1"""
        )
        row = rows[0] if rows else None
        if row is None:
            return {
                "status": "NOT_RUN",
                "execution_allowed": False,
                "live_certified": False,
            }
        keys = (
            "run_id", "generated_at", "status", "observation_count", "simulations",
            "horizon_trades", "block_size", "seed", "starting_equity_r",
            "ruin_drawdown_pct", "expected_final_equity_r", "median_final_equity_r",
            "final_equity_p05_r", "final_equity_p95_r", "median_max_drawdown_pct",
            "max_drawdown_p95_pct", "probability_of_ruin",
            "probability_final_below_start", "reason", "symbol", "decision", "regime",
        )
        result = dict(zip(keys, row, strict=True))
        result.update({"execution_allowed": False, "live_certified": False})
        return result

    async def _persist(
        self,
        report: MonteCarloReport,
        symbol: str | None,
        decision: str | None,
        regime: str | None,
    ) -> None:
        await self.database.execute(
            """INSERT INTO monte_carlo_runs(
            run_id, generated_at, status, observation_count, simulations, horizon_trades,
            block_size, seed, starting_equity_r, ruin_drawdown_pct,
            expected_final_equity_r, median_final_equity_r, final_equity_p05_r,
            final_equity_p95_r, median_max_drawdown_pct, max_drawdown_p95_pct,
            probability_of_ruin, probability_final_below_start, reason, symbol, decision, regime
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                report.run_id,
                report.generated_at.astimezone(UTC).isoformat(),
                report.status,
                report.observation_count,
                report.simulations,
                report.horizon_trades,
                report.block_size,
                report.seed,
                report.starting_equity_r,
                report.ruin_drawdown_pct,
                report.expected_final_equity_r,
                report.median_final_equity_r,
                report.final_equity_p05_r,
                report.final_equity_p95_r,
                report.median_max_drawdown_pct,
                report.max_drawdown_p95_pct,
                report.probability_of_ruin,
                report.probability_final_below_start,
                report.reason,
                symbol,
                decision,
                regime,
            ),
        )

    @staticmethod
    def _moving_block_sample(
        values: Sequence[float], horizon: int, block_size: int, rng: random.Random
    ) -> list[float]:
        if not values:
            return []
        block = min(block_size, len(values))
        result: list[float] = []
        maximum_start = len(values) - block
        while len(result) < horizon:
            start = rng.randint(0, maximum_start) if maximum_start > 0 else 0
            result.extend(values[start : start + block])
        return result[:horizon]

    @staticmethod
    def _quantile(values: Sequence[float], probability: float) -> float:
        if not values:
            raise ValueError("quantile requires values")
        ordered = sorted(values)
        position = (len(ordered) - 1) * probability
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return ordered[lower]
        weight = position - lower
        return ordered[lower] * (1.0 - weight) + ordered[upper] * weight
