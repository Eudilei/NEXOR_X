from decimal import Decimal

from nexor_x.accounting.net_pnl import (
    FeeModel,
    NetPnLCalculator,
)


def test_net_pnl_subtracts_entry_and_exit_fees() -> None:
    calc = NetPnLCalculator(
        FeeModel(
            maker_rate=Decimal("0.001"),
            taker_rate=Decimal("0.001"),
        )
    )

    result = calc.calculate(
        gross_pnl=4.8,
        entry_notional=180,
        exit_notional=200,
    )

    assert result.entry_fee == Decimal("0.180")
    assert result.exit_fee == Decimal("0.200")
    assert result.total_fees == Decimal("0.380")
    assert result.net_pnl == Decimal("4.420")


def test_explicit_exchange_fees_override_estimate() -> None:
    calc = NetPnLCalculator()

    result = calc.calculate(
        gross_pnl=10,
        entry_notional=1000,
        exit_notional=1100,
        entry_fee=0.31,
        exit_fee=0.37,
    )

    assert result.total_fees == Decimal("0.68")
    assert result.net_pnl == Decimal("9.32")


def test_loss_becomes_more_negative_after_fees() -> None:
    calc = NetPnLCalculator(
        FeeModel(
            maker_rate=Decimal("0.001"),
            taker_rate=Decimal("0.001"),
        )
    )

    result = calc.calculate(
        gross_pnl=-5,
        entry_notional=100,
        exit_notional=95,
    )

    assert result.total_fees == Decimal("0.195")
    assert result.net_pnl == Decimal("-5.195")


def test_dict_keeps_gross_fees_and_net() -> None:
    calc = NetPnLCalculator()
    result = calc.calculate(
        gross_pnl=2,
        entry_notional=100,
        exit_notional=102,
        entry_fee=0.1,
        exit_fee=0.1,
    ).as_dict()

    assert set(result) == {
        "gross_pnl",
        "entry_fee",
        "exit_fee",
        "total_fees",
        "net_pnl",
    }
    assert result["net_pnl"] == 1.8
