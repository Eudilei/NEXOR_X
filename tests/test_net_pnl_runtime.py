from decimal import Decimal

from nexor_x.accounting.net_pnl import (
    FeeModel,
    NetPnLCalculator,
)
from nexor_x.accounting.runtime_integration import (
    NetPerformanceAggregator,
    NetPnLRuntimeAdapter,
)


def test_closed_trade_main_pnl_becomes_net() -> None:
    calc = NetPnLCalculator(
        FeeModel(
            maker_rate=Decimal("0.001"),
            taker_rate=Decimal("0.001"),
        )
    )
    adapter = NetPnLRuntimeAdapter(calc)

    trade = adapter.normalize_closed_trade({
        "pnl": 4.8,
        "entry_notional": 180,
        "exit_notional": 200,
    })

    assert trade["gross_pnl"] == 4.8
    assert trade["total_fees"] == 0.38
    assert trade["net_pnl"] == 4.42
    assert trade["pnl"] == 4.42
    assert trade["realized_pnl"] == 4.42
    assert trade["pnl_basis"] == "NET_AFTER_FEES"


def test_explicit_exchange_fees_are_preserved() -> None:
    adapter = NetPnLRuntimeAdapter()

    trade = adapter.normalize_closed_trade({
        "gross_pnl": 10,
        "entry_notional": 1000,
        "exit_notional": 1100,
        "entry_fee": 0.31,
        "exit_fee": 0.37,
    })

    assert trade["total_fees"] == 0.68
    assert trade["net_pnl"] == 9.32


def test_profit_factor_uses_net_pnl() -> None:
    agg = NetPerformanceAggregator()

    report = agg.summarize([
        {"net_pnl": 10, "gross_pnl": 12},
        {"net_pnl": -5, "gross_pnl": -4},
        {"net_pnl": 5, "gross_pnl": 7},
    ])

    assert report["net_pnl"] == 10.0
    assert report["profit_factor"] == 3.0
    assert report["pnl_basis"] == "NET_AFTER_FEES"


def test_legacy_trade_fallback() -> None:
    agg = NetPerformanceAggregator()

    assert agg.trade_pnl({"pnl": 2.5}) == Decimal("2.5")
    assert agg.trade_pnl({"realized_pnl": -1.5}) == Decimal("-1.5")
