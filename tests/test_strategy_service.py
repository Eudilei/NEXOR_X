from __future__ import annotations

from pathlib import Path

import pytest

from nexor_x.infrastructure.database import DatabaseService
from nexor_x.strategy.service import StrategyOrchestrationService


@pytest.mark.asyncio
async def test_service_persists_and_returns_selection(tmp_path: Path) -> None:
    database = DatabaseService(tmp_path / "strategy.db")
    await database.start()
    try:
        service = StrategyOrchestrationService(database)
        await service.start()

        result = await service.rank(
            symbol="BTCUSDT",
            regime="TREND_UP",
            decision="LONG_BIAS",
            metrics=[
                {
                    "strategy_id": "trend_pullback",
                    "sample_count": 200,
                    "profit_factor": 1.70,
                    "expected_r": 0.28,
                    "win_rate": 0.60,
                    "max_drawdown_r": 1.2,
                    "brier_score": 0.19,
                    "walk_forward_pass_ratio": 0.80,
                    "monte_carlo_ruin_probability": 0.02,
                }
            ],
        )
        assert result["selected_strategy_id"] == "trend_pullback"
        assert result["execution_allowed"] is False

        status = await service.status()
        assert status["strategy_count"] >= 5
        assert status["latest_selection"]["selected_strategy_id"] == "trend_pullback"
    finally:
        await database.stop()


@pytest.mark.asyncio
async def test_service_rejects_unvalidated_metric(tmp_path: Path) -> None:
    database = DatabaseService(tmp_path / "strategy.db")
    await database.start()
    try:
        service = StrategyOrchestrationService(database)
        await service.start()
        result = await service.rank(
            symbol="BTCUSDT",
            regime="TREND_UP",
            decision="LONG_BIAS",
            metrics=[
                {
                    "strategy_id": "trend_pullback",
                    "sample_count": 10,
                    "profit_factor": 0.80,
                    "expected_r": -0.10,
                    "win_rate": 0.40,
                    "max_drawdown_r": 4.0,
                    "brier_score": 0.40,
                    "walk_forward_pass_ratio": 0.20,
                    "monte_carlo_ruin_probability": 0.30,
                }
            ],
        )
        assert result["selected_strategy_id"] is None
        assert result["status"] == "NO_ELIGIBLE_STRATEGY"
    finally:
        await database.stop()
