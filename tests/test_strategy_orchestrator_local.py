from nexor_x.strategy import (
    MetaStrategyOrchestrator,
    StrategyDefinition,
    StrategyMetric,
    StrategyStatus,
)

def test_rank_is_observational():
    engine = MetaStrategyOrchestrator([
        StrategyDefinition(
            strategy_id="trend_pullback",
            name="Trend Pullback",
            supported_regimes=("TREND_UP",),
            supported_directions=("LONG_BIAS",),
            status=StrategyStatus.RESEARCH,
        )
    ])
    result = engine.rank(
        symbol="BTCUSDT",
        regime="TREND_UP",
        decision="LONG_BIAS",
        metrics=[
            StrategyMetric(
                strategy_id="trend_pullback",
                regime="TREND_UP",
                decision="LONG_BIAS",
                sample_count=100,
                profit_factor=1.5,
                expected_r=0.2,
                win_rate=0.58,
                max_drawdown_r=1.0,
                brier_score=0.2,
                walk_forward_pass_ratio=0.8,
                monte_carlo_ruin_probability=0.02,
            )
        ],
    )
    assert result.selected_strategy_id == "trend_pullback"
    assert result.execution_allowed is False
