from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from nexor_x.domain import OperatingMode
from nexor_x.infrastructure.database import DatabaseService

from .models import PaperFill, PaperOrderStatus


class PaperExecutionService:
    """Deterministic PAPER execution with fees, slippage and persistent positions.

    This service never calls an exchange order endpoint. It only accepts a readiness
    result already approved by the authoritative PreTradeGate.
    """

    def __init__(
        self,
        database: DatabaseService,
        *,
        fee_rate: float,
        slippage_rate: float,
        stop_loss_pct: float,
        max_notional_multiple: float,
    ) -> None:
        if not 0 <= fee_rate < 1 or not 0 <= slippage_rate < 1:
            raise ValueError("fee/slippage rates must be in [0, 1)")
        if not 0 < stop_loss_pct < 1:
            raise ValueError("stop_loss_pct must be in (0, 1)")
        if max_notional_multiple <= 0:
            raise ValueError("max_notional_multiple must be positive")
        self.database = database
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate
        self.stop_loss_pct = stop_loss_pct
        self.max_notional_multiple = max_notional_multiple
        self._lock = asyncio.Lock()

    async def open_from_readiness(
        self,
        *,
        mode: OperatingMode,
        readiness: dict[str, Any],
        market: dict[str, Any],
        portfolio: dict[str, Any],
    ) -> PaperFill:
        now = datetime.now(UTC)
        symbol = str(readiness.get("symbol", "")).upper()
        side = str(readiness.get("side") or "")
        allowed = bool(readiness.get("allowed"))
        if mode is not OperatingMode.PAPER:
            return self._rejected(symbol, side, "LIVE proibido no PaperExecutionService", now)
        if not allowed or readiness.get("decision") != "READY_FOR_PAPER":
            return self._rejected(symbol, side, "Pre-Trade Gate nao aprovou a operacao", now)
        if side not in {"LONG", "SHORT"}:
            return self._rejected(symbol, side, "lado invalido", now)
        snapshot = market.get("snapshot", {})
        if bool(snapshot.get("stale", True)):
            return self._rejected(symbol, side, "dados de mercado antigos", now)
        reference_price = float(snapshot.get("price") or 0.0)
        if reference_price <= 0:
            return self._rejected(symbol, side, "preco de mercado invalido", now)
        risk_budget = float(readiness.get("risk_budget") or 0.0)
        equity = float(portfolio.get("equity") or 0.0)
        leverage = float(readiness.get("leverage") or 1.0)
        if risk_budget <= 0 or equity <= 0:
            return self._rejected(symbol, side, "orcamento de risco invalido", now)

        adverse = self.slippage_rate if side == "LONG" else -self.slippage_rate
        entry_price = reference_price * (1.0 + adverse)
        stop_distance = entry_price * self.stop_loss_pct
        risk_based_notional = risk_budget / self.stop_loss_pct
        max_notional = equity * min(leverage, self.max_notional_multiple)
        notional = min(risk_based_notional, max_notional)
        quantity = notional / entry_price
        stop_price = entry_price - stop_distance if side == "LONG" else entry_price + stop_distance
        fee = notional * self.fee_rate
        if quantity <= 0 or notional <= 0:
            return self._rejected(symbol, side, "dimensionamento invalido", now)

        async with self._lock:
            duplicates = await self.database.fetchall(
                "SELECT id FROM portfolio_positions WHERE symbol=? AND status='OPEN'",
                (symbol,),
            )
            if duplicates:
                return self._rejected(symbol, side, "ja existe posicao aberta no simbolo", now)
            position_id = await self.database.execute_returning_id(
                """INSERT INTO portfolio_positions
                (symbol, side, quantity, entry_price, notional, status, opened_at,
                 stop_price, entry_fee, realized_pnl, exit_price, exit_fee, close_reason)
                VALUES (?, ?, ?, ?, ?, 'OPEN', ?, ?, ?, 0.0, NULL, 0.0, NULL)""",
                (symbol, side, quantity, entry_price, notional, now.isoformat(), stop_price, fee),
            )
        return PaperFill(
            position_id=position_id,
            symbol=symbol,
            side=side,
            status=PaperOrderStatus.FILLED,
            quantity=round(quantity, 12),
            entry_price=round(entry_price, 12),
            stop_price=round(stop_price, 12),
            notional=round(notional, 8),
            risk_budget=round(risk_budget, 8),
            fee_paid=round(fee, 8),
            reason="PAPER fill persistido; nenhuma ordem LIVE foi enviada",
            created_at=now,
        )

    async def close_position(self, position_id: int, market_price: float, reason: str) -> dict[str, Any]:
        if market_price <= 0:
            raise ValueError("market_price must be positive")
        async with self._lock:
            rows = await self.database.fetchall(
                """SELECT symbol, side, quantity, entry_price, notional, entry_fee
                FROM portfolio_positions WHERE id=? AND status='OPEN'""",
                (position_id,),
            )
            if not rows:
                raise ValueError("open position not found")
            symbol, side, quantity, entry_price, notional, entry_fee = rows[0]
            quantity_f = float(quantity)
            entry_f = float(entry_price)
            exit_price = market_price * (1.0 - self.slippage_rate if side == "LONG" else 1.0 + self.slippage_rate)
            gross = (exit_price - entry_f) * quantity_f if side == "LONG" else (entry_f - exit_price) * quantity_f
            exit_fee = abs(float(notional)) * self.fee_rate
            net = gross - float(entry_fee) - exit_fee
            now = datetime.now(UTC).isoformat()
            await self.database.execute(
                """UPDATE portfolio_positions SET status='CLOSED', closed_at=?, exit_price=?,
                exit_fee=?, realized_pnl=?, close_reason=? WHERE id=? AND status='OPEN'""",
                (now, exit_price, exit_fee, net, reason[:120], position_id),
            )
            await self.database.execute(
                """UPDATE portfolio_accounts SET equity=equity+?, realized_pnl=realized_pnl+?,
                peak_equity=MAX(peak_equity, equity+?), updated_at=? WHERE account_id='PAPER'""",
                (net, net, net, now),
            )
        return {
            "position_id": position_id,
            "symbol": symbol,
            "side": side,
            "exit_price": round(exit_price, 12),
            "gross_pnl": round(gross, 8),
            "fees": round(float(entry_fee) + exit_fee, 8),
            "net_pnl": round(net, 8),
            "reason": reason[:120],
            "live_order_sent": False,
        }

    @staticmethod
    def _rejected(symbol: str, side: str, reason: str, now: datetime) -> PaperFill:
        return PaperFill(None, symbol, side, PaperOrderStatus.REJECTED, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, reason, now)
