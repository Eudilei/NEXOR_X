from nexor_x.domain import OperatingMode
from nexor_x.risk import GateDecision, PreTradeGate


def gate() -> PreTradeGate:
    return PreTradeGate(
        minimum_expected_r=0.05,
        minimum_profit_factor=1.10,
        minimum_calibration_samples=30,
        risk_per_trade_pct=10.0,
        leverage=15.0,
        max_open_positions=10,
        hard_stop_drawdown_pct=25.0,
    )


def valid_inputs():
    market = {"snapshot": {"stale": False}}
    quant = {
        "decision": "LONG_BIAS",
        "calibrated": True,
        "expected_r": 0.20,
        "profit_factor": 1.40,
        "calibration_samples": 80,
    }
    portfolio = {"equity": 100.0, "drawdown_pct": 2.0, "open_positions": 1}
    return market, quant, portfolio


def test_ready_for_paper_calculates_risk_budget():
    market, quant, portfolio = valid_inputs()
    result = gate().evaluate(
        symbol="BTCUSDT", mode=OperatingMode.PAPER,
        market=market, quant=quant, portfolio=portfolio,
    )
    assert result.decision is GateDecision.READY_FOR_PAPER
    assert result.allowed is True
    assert result.risk_budget == 10.0
    assert result.side == "LONG"
    assert result.to_dict()["order_created"] is False


def test_uncalibrated_context_is_blocked():
    market, quant, portfolio = valid_inputs()
    quant["calibrated"] = False
    result = gate().evaluate(
        symbol="BTCUSDT", mode=OperatingMode.PAPER,
        market=market, quant=quant, portfolio=portfolio,
    )
    assert result.decision is GateDecision.BLOCKED
    assert result.risk_budget == 0.0


def test_stale_market_is_blocked():
    market, quant, portfolio = valid_inputs()
    market["snapshot"]["stale"] = True
    result = gate().evaluate(
        symbol="BTCUSDT", mode=OperatingMode.PAPER,
        market=market, quant=quant, portfolio=portfolio,
    )
    assert result.decision is GateDecision.BLOCKED
    assert result.checks["fresh_market_data"] is False


def test_hard_stop_has_priority():
    market, quant, portfolio = valid_inputs()
    portfolio["drawdown_pct"] = 25.0
    result = gate().evaluate(
        symbol="BTCUSDT", mode=OperatingMode.PAPER,
        market=market, quant=quant, portfolio=portfolio,
    )
    assert result.decision is GateDecision.HARD_STOP


def test_live_is_forbidden_even_with_valid_edge():
    market, quant, portfolio = valid_inputs()
    result = gate().evaluate(
        symbol="BTCUSDT", mode=OperatingMode.LIVE,
        market=market, quant=quant, portfolio=portfolio,
    )
    assert result.decision is GateDecision.LIVE_FORBIDDEN
    assert result.allowed is False
