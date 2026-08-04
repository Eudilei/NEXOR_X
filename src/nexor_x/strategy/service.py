from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Iterable

from .models import StrategyDefinition, StrategyMetric, StrategyStatus
from .orchestrator import MetaStrategyOrchestrator, OrchestratorPolicy
from .repository import StrategyRepository


DEFAULT_STRATEGIES: tuple[StrategyDefinition, ...] = (
    StrategyDefinition(
        strategy_id="trend_pullback",
        name="Trend Pullback",
        supported_regimes=("TREND_UP", "TREND_DOWN"),
        supported_directions=("LONG_BIAS", "SHORT_BIAS"),
        status=StrategyStatus.RESEARCH,
        description="Pullback alinhado a tendencia confirmada.",
    ),
    StrategyDefinition(
        strategy_id="breakout",
        name="Breakout",
        supported_regimes=("COMPRESSION", "EXPANSION"),
        supported_directions=("LONG_BIAS", "SHORT_BIAS"),
        status=StrategyStatus.RESEARCH,
        description="Rompimento apos compressao ou expansao validada.",
    ),
    StrategyDefinition(
        strategy_id="mean_reversion",
        name="Mean Reversion",
        supported_regimes=("RANGE",),
        supported_directions=("LONG_BIAS", "SHORT_BIAS"),
        status=StrategyStatus.RESEARCH,
        description="Retorno a media em regime lateral.",
    ),
    StrategyDefinition(
        strategy_id="momentum",
        name="Momentum",
        supported_regimes=("TREND_UP", "TREND_DOWN", "EXPANSION"),
        supported_directions=("LONG_BIAS", "SHORT_BIAS"),
        status=StrategyStatus.RESEARCH,
        description="Continuidade de momentum com confirmacao contextual.",
    ),
    StrategyDefinition(
        strategy_id="liquidity_sweep",
        name="Liquidity Sweep",
        supported_regimes=("RANGE", "EXPANSION"),
        supported_directions=("LONG_BIAS", "SHORT_BIAS"),
        status=StrategyStatus.RESEARCH,
        description="Reversao apos varredura de liquidez.",
    ),
)


class StrategyOrchestrationService:
    """Coordinates persistence and ranking without authorizing execution."""

    def __init__(
        self,
        database: Any,
        definitions: Iterable[StrategyDefinition] = DEFAULT_STRATEGIES,
        policy: OrchestratorPolicy | None = None,
    ) -> None:
        self.repository = StrategyRepository(database)
        self.orchestrator = MetaStrategyOrchestrator(definitions, policy)

    async def start(self) -> None:
        await self.repository.ensure_schema()
        for definition in self.orchestrator.definitions:
            await self.repository.upsert_definition(definition)

    async def status(self) -> dict[str, Any]:
        definitions = await self.repository.list_definitions()
        latest = await self.repository.latest_selection()
        return {
            "state": "READY",
            "strategy_count": len(definitions),
            "strategies": [item.to_dict() for item in definitions],
            "latest_selection": latest,
            "execution_allowed": False,
            "live_certified": False,
        }

    async def rank(
        self,
        *,
        symbol: str,
        regime: str,
        decision: str,
        metrics: Iterable[dict[str, Any]],
        current_strategy_id: str | None = None,
    ) -> dict[str, Any]:
        parsed: list[StrategyMetric] = []
        for item in metrics:
            metric = StrategyMetric(
                strategy_id=str(item["strategy_id"]),
                regime=regime.strip().upper(),
                decision=decision.strip().upper(),
                sample_count=int(item["sample_count"]),
                profit_factor=float(item["profit_factor"]),
                expected_r=float(item["expected_r"]),
                win_rate=float(item["win_rate"]),
                max_drawdown_r=float(item["max_drawdown_r"]),
                brier_score=(
                    None if item.get("brier_score") is None
                    else float(item["brier_score"])
                ),
                walk_forward_pass_ratio=(
                    None
                    if item.get("walk_forward_pass_ratio") is None
                    else float(item["walk_forward_pass_ratio"])
                ),
                monte_carlo_ruin_probability=(
                    None
                    if item.get("monte_carlo_ruin_probability") is None
                    else float(item["monte_carlo_ruin_probability"])
                ),
                updated_at=datetime.now(UTC),
            )
            parsed.append(metric)
            await self.repository.save_metric(metric)

        selection = self.orchestrator.rank(
            symbol=symbol,
            regime=regime,
            decision=decision,
            metrics=parsed,
            current_strategy_id=current_strategy_id,
        )
        await self.repository.save_selection(selection)
        return selection.to_dict()
