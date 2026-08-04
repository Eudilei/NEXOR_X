from nexor_x.allocation import (
    AdaptivePortfolioAllocator,
    AllocationCandidate,
    AllocationPolicy,
)


def candidate(
    strategy_id: str,
    symbol: str,
    *,
    score: float = 0.8,
    expected_r: float = 0.25,
    profit_factor: float = 1.5,
    group: str = "MAJOR",
) -> AllocationCandidate:
    return AllocationCandidate(
        strategy_id=strategy_id,
        symbol=symbol,
        direction="LONG_BIAS",
        score=score,
        expected_r=expected_r,
        profit_factor=profit_factor,
        walk_forward_pass_ratio=0.8,
        monte_carlo_ruin_probability=0.02,
        max_drawdown_r=2.0,
        correlation_group=group,
    )


def test_allocates_only_eligible_candidates() -> None:
    allocator = AdaptivePortfolioAllocator()
    bad = candidate("bad", "XRPUSDT", profit_factor=0.8)
    plan = allocator.allocate(
        [candidate("trend", "BTCUSDT"), bad],
        portfolio_drawdown_pct=0.0,
    )
    assert plan.status == "RESEARCH_ALLOCATION_READY"
    assert [item.strategy_id for item in plan.allocations] == ["trend"]
    assert plan.execution_allowed is False
    assert plan.live_certified is False


def test_correlation_group_limit_is_enforced() -> None:
    allocator = AdaptivePortfolioAllocator(
        AllocationPolicy(
            maximum_weight_per_candidate=0.6,
            maximum_weight_per_correlation_group=0.55,
        )
    )
    plan = allocator.allocate(
        [
            candidate("btc", "BTCUSDT", group="MAJOR"),
            candidate("eth", "ETHUSDT", group="MAJOR"),
            candidate("sol", "SOLUSDT", group="ALT"),
        ],
        portfolio_drawdown_pct=0.0,
    )
    major_weight = sum(
        item.target_weight
        for item in plan.allocations
        if item.symbol in {"BTCUSDT", "ETHUSDT"}
    )
    assert major_weight <= 0.55 + 1e-9


def test_recovery_reduces_total_risk_budget() -> None:
    policy = AllocationPolicy(
        maximum_portfolio_risk_pct=10.0,
        recovery_drawdown_trigger_pct=10.0,
        recovery_risk_multiplier=0.30,
    )
    allocator = AdaptivePortfolioAllocator(policy)
    plan = allocator.allocate(
        [candidate("trend", "BTCUSDT")],
        portfolio_drawdown_pct=12.0,
    )
    assert plan.status == "RECOVERY_ALLOCATION"
    assert plan.total_risk_budget_pct <= 3.0 + 1e-9


def test_hard_stop_blocks_allocation() -> None:
    allocator = AdaptivePortfolioAllocator()
    plan = allocator.allocate(
        [candidate("trend", "BTCUSDT")],
        portfolio_drawdown_pct=25.0,
    )
    assert plan.status == "HARD_STOP"
    assert plan.allocations == ()
    assert plan.total_risk_budget_pct == 0.0


def test_empty_eligible_set_is_explicit() -> None:
    allocator = AdaptivePortfolioAllocator()
    plan = allocator.allocate(
        [candidate("bad", "BTCUSDT", expected_r=-0.1)],
        portfolio_drawdown_pct=0.0,
    )
    assert plan.status == "NO_ELIGIBLE_CANDIDATES"
    assert plan.allocations[0].eligible is False
    assert "EXPECTED_R_BELOW_MINIMUM" in plan.allocations[0].reasons
