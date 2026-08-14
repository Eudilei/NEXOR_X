from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


@dataclass(frozen=True)
class FeeModel:
    maker_rate: Decimal = Decimal("0.0002")
    taker_rate: Decimal = Decimal("0.0005")

    def rate_for(self, liquidity: str) -> Decimal:
        side = str(liquidity).strip().lower()
        if side == "maker":
            return self.maker_rate
        return self.taker_rate


@dataclass(frozen=True)
class NetPnLBreakdown:
    gross_pnl: Decimal
    entry_fee: Decimal
    exit_fee: Decimal
    total_fees: Decimal
    net_pnl: Decimal

    def as_dict(self) -> dict[str, float]:
        return {
            "gross_pnl": float(self.gross_pnl),
            "entry_fee": float(self.entry_fee),
            "exit_fee": float(self.exit_fee),
            "total_fees": float(self.total_fees),
            "net_pnl": float(self.net_pnl),
        }


class NetPnLCalculator:
    """Calcula PnL líquido preservando componentes para auditoria."""

    def __init__(self, fee_model: FeeModel | None = None) -> None:
        self.fee_model = fee_model or FeeModel()

    def calculate(
        self,
        *,
        gross_pnl: Any,
        entry_notional: Any,
        exit_notional: Any,
        entry_liquidity: str = "taker",
        exit_liquidity: str = "taker",
        entry_fee: Any | None = None,
        exit_fee: Any | None = None,
    ) -> NetPnLBreakdown:
        gross = _d(gross_pnl)
        entry_n = abs(_d(entry_notional))
        exit_n = abs(_d(exit_notional))

        resolved_entry_fee = (
            _d(entry_fee)
            if entry_fee is not None
            else entry_n * self.fee_model.rate_for(entry_liquidity)
        )
        resolved_exit_fee = (
            _d(exit_fee)
            if exit_fee is not None
            else exit_n * self.fee_model.rate_for(exit_liquidity)
        )

        total = resolved_entry_fee + resolved_exit_fee
        net = gross - total

        return NetPnLBreakdown(
            gross_pnl=gross,
            entry_fee=resolved_entry_fee,
            exit_fee=resolved_exit_fee,
            total_fees=total,
            net_pnl=net,
        )
