from __future__ import annotations

from dataclasses import asdict, is_dataclass
from decimal import Decimal
from typing import Any, Mapping

from .net_pnl import NetPnLCalculator


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "__dict__"):
        return dict(vars(value))
    raise TypeError("trade deve ser mapping, dataclass ou objeto com __dict__")


def _first(data: Mapping[str, Any], *names: str, default: Any = 0) -> Any:
    for name in names:
        if name in data and data[name] is not None:
            return data[name]
    return default


class NetPnLRuntimeAdapter:
    """Normaliza um trade fechado para PnL líquido sem perder auditoria."""

    def __init__(self, calculator: NetPnLCalculator | None = None) -> None:
        self.calculator = calculator or NetPnLCalculator()

    def normalize_closed_trade(
        self,
        trade: Any,
    ) -> dict[str, Any]:
        data = _as_mapping(trade)

        gross_pnl = _first(
            data,
            "gross_pnl",
            "realized_pnl",
            "pnl",
            default=0,
        )
        entry_notional = _first(
            data,
            "entry_notional",
            "notional_entry",
            "cost",
            default=0,
        )
        exit_notional = _first(
            data,
            "exit_notional",
            "notional_exit",
            "proceeds",
            default=0,
        )

        entry_fee = data.get("entry_fee")
        exit_fee = data.get("exit_fee")

        result = self.calculator.calculate(
            gross_pnl=gross_pnl,
            entry_notional=entry_notional,
            exit_notional=exit_notional,
            entry_liquidity=str(
                data.get("entry_liquidity", "taker")
            ),
            exit_liquidity=str(
                data.get("exit_liquidity", "taker")
            ),
            entry_fee=entry_fee,
            exit_fee=exit_fee,
        )

        data.update(result.as_dict())

        # pnl/realized_pnl tornam-se aliases operacionais do líquido.
        data["pnl"] = float(result.net_pnl)
        data["realized_pnl"] = float(result.net_pnl)
        data["pnl_basis"] = "NET_AFTER_FEES"

        return data


class NetPerformanceAggregator:
    """Agrega métricas usando resultado líquido como fonte primária."""

    def trade_pnl(self, trade: Any) -> Decimal:
        data = _as_mapping(trade)
        return Decimal(str(_first(
            data,
            "net_pnl",
            "pnl",
            "realized_pnl",
            default=0,
        )))

    def summarize(
        self,
        trades: list[Any],
    ) -> dict[str, float | int | str]:
        pnls = [self.trade_pnl(t) for t in trades]

        gross_profit = sum(
            (p for p in pnls if p > 0),
            Decimal("0"),
        )
        gross_loss_abs = abs(sum(
            (p for p in pnls if p < 0),
            Decimal("0"),
        ))
        net_total = sum(pnls, Decimal("0"))

        if gross_loss_abs > 0:
            profit_factor = gross_profit / gross_loss_abs
        elif gross_profit > 0:
            profit_factor = Decimal("999999")
        else:
            profit_factor = Decimal("0")

        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p < 0)

        return {
            "closed_trades": len(pnls),
            "wins": wins,
            "losses": losses,
            "net_pnl": float(net_total),
            "net_profit": float(gross_profit),
            "net_loss_abs": float(gross_loss_abs),
            "profit_factor": float(profit_factor),
            "pnl_basis": "NET_AFTER_FEES",
        }
