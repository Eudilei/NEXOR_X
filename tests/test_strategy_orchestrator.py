from nexor_x.strategy import (
    MetaStrategyOrchestrator,
    OrchestratorPolicy,
    StrategyDefinition,
    StrategyMetric,
    StrategyStatus,
)


def definition(strategy_id: str) -> StrategyDefinition:
    return StrategyDefinition(
        strategy_id=strategy_id,
        name=strategy_id,
        supported_regimes=("TREND_UP",),
        supported_directions=("LONG_BIAS",),
        status=StrategyStatus.PAPER,
    )


def metric(
    strategy_id: str,
    *,
    expected_r: float = 0.20,
    profit_factor: float = 1.40,
    samples: int = 120,
    walk_forward: float = 0.80,
    ruin: float = 0.02,
    brier: float = 0.20,
    drawdown: float = 1.0,
) -> StrategyMetric:
    return StrategyMetric(
        strategy_id=strategy_id,
        regime="TREND_UP",
        decision="LONG_BIAS",
        sample_count=samples,
        profit_factor=profit_factor,
        expected_r=expected_r,
        win_rate=0.58,
        max_drawdown_r=drawdown,
        brier_score=brier,
        walk_forward_pass_ratio=walk_forward,
        monte_carlo_ruin_probability=ruin,
    )


def test_selects_best_eligible_strategy() -> None:
    engine = MetaStrategyOrchestrator([definition("pullback"), definition("breakout")])
    result = engine.rank(
        symbol="BTCUSDT",
        regime="TREND_UP",
        decision="LONG_BIAS",
        metrics=[
            metric("pullback", expected_r=0.32, profit_factor=1.80),
            metric("breakout", expected_r=0.15, profit_factor=1.25),
        ],
    )
    assert result.selected_strategy_id == "pullback"
    assert result.status == "SELECTED_FOR_RESEARCH"
    assert result.execution_allowed is False
    assert result.live_certified is False


def test_rejects_strategy_without_robustness() -> None:
    engine = MetaStrategyOrchestrator([definition("pullback")])
    result = engine.rank(
        symbol="BTCUSDT",
        regime="TREND_UP",
        decision="LONG_BIAS",
        metrics=[metric("pullback", walk_forward=0.20, ruin=0.20)],
    )
    assert result.selected_strategy_id is None
    assert "WALK_FORWARD_NOT_APPROVED" in result.rankings[0].reasons
    assert "MONTE_CARLO_RISK_TOO_HIGH" in result.rankings[0].reasons


def test_hysteresis_avoids_unnecessary_switching() -> None:
    policy = OrchestratorPolicy(switch_hysteresis=0.20)
    engine = MetaStrategyOrchestrator(
        [definition("pullback"), definition("breakout")],
        policy,
    )
    result = engine.rank(
        symbol="BTCUSDT",
        regime="TREND_UP",
        decision="LONG_BIAS",
        current_strategy_id="breakout",
        metrics=[
            metric("pullback", expected_r=0.25, profit_factor=1.55),
            metric("breakout", expected_r=0.23, profit_factor=1.50),
        ],
    )
    assert result.selected_strategy_id == "breakout"


def test_ignores_unsupported_context() -> None:
    engine = MetaStrategyOrchestrator([definition("pullback")])
    result = engine.rank(
        symbol="ETHUSDT",
        regime="RANGE",
        decision="SHORT_BIAS",
        metrics=[metric("pullback")],
    )
    assert result.selected_strategy_id is None
    assert result.rankings == ()


def test_retired_strategy_is_not_ranked() -> None:
    retired = StrategyDefinition(
        strategy_id="legacy",
        name="Legacy",
        supported_regimes=("TREND_UP",),
        supported_directions=("LONG_BIAS",),
        status=StrategyStatus.RETIRED,
    )
    engine = MetaStrategyOrchestrator([retired])
    result = engine.rank(
        symbol="BTCUSDT",
        regime="TREND_UP",
        decision="LONG_BIAS",
        metrics=[metric("legacy")],
    )
    assert result.selected_strategy_id is None
