from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nexor_x.execution import PaperExecutionService
from nexor_x.infrastructure.database import DatabaseService


@dataclass(frozen=True, slots=True)
class PositionPolicy:
    break_even_trigger_r: float = 0.8
    break_even_buffer_r: float = 0.05
    partial_trigger_r: float = 1.5
    partial_fraction: float = 0.35
    trailing_start_r: float = 2.0
    trailing_distance_r: float = 0.8


class PositionManagementService:
    """Deterministic PAPER position manager.

    It protects downside first, realizes one controlled partial and then trails the
    remaining quantity. It does not predict tops and never sends LIVE orders.
    """

    def __init__(
        self,
        database: DatabaseService,
        execution: PaperExecutionService,
        policy: PositionPolicy | None = None,
    ) -> None:
        self.database = database
        self.execution = execution
        self.policy = policy or PositionPolicy()
        p = self.policy
        if not (0 < p.partial_fraction < 1):
            raise ValueError("partial_fraction must be in (0, 1)")
        if min(p.break_even_trigger_r, p.partial_trigger_r, p.trailing_start_r) <= 0:
            raise ValueError("R triggers must be positive")

    async def evaluate(self, position_id: int, market_price: float) -> dict[str, Any]:
        if market_price <= 0:
            raise ValueError("market_price must be positive")
        rows = await self.database.fetchall(
            """SELECT symbol, side, quantity, entry_price, stop_price, initial_stop_price,
            highest_price, lowest_price, partial_taken, status
            FROM portfolio_positions WHERE id=?""",
            (position_id,),
        )
        if not rows:
            raise ValueError("position not found")
        (symbol, side, quantity, entry, stop, initial_stop, highest, lowest,
         partial_taken, status) = rows[0]
        if status != "OPEN":
            raise ValueError("position is not open")
        side = str(side)
        entry = float(entry)
        stop = float(stop)
        initial_stop = float(initial_stop if initial_stop is not None else stop)
        quantity = float(quantity)
        highest = max(float(highest or entry), market_price)
        lowest = min(float(lowest or entry), market_price)
        risk_per_unit = abs(entry - initial_stop)
        if risk_per_unit <= 0:
            raise ValueError("invalid initial risk distance")
        favorable = market_price - entry if side == "LONG" else entry - market_price
        current_r = favorable / risk_per_unit
        actions: list[dict[str, Any]] = []

        await self.database.execute(
            "UPDATE portfolio_positions SET highest_price=?, lowest_price=? WHERE id=?",
            (highest, lowest, position_id),
        )

        stop_hit = market_price <= stop if side == "LONG" else market_price >= stop
        if stop_hit:
            closed = await self.execution.close_position(position_id, market_price, "PROTECTIVE_STOP")
            actions.append({"type": "CLOSE", "reason": "PROTECTIVE_STOP", "result": closed})
            return self._result(position_id, symbol, current_r, stop, actions, True)

        if current_r >= self.policy.break_even_trigger_r:
            buffer = risk_per_unit * self.policy.break_even_buffer_r
            candidate = entry + buffer if side == "LONG" else entry - buffer
            improved = candidate > stop if side == "LONG" else candidate < stop
            if improved:
                stop = candidate
                await self.database.execute(
                    "UPDATE portfolio_positions SET stop_price=? WHERE id=?", (stop, position_id)
                )
                actions.append({"type": "MOVE_STOP", "reason": "BREAK_EVEN", "stop_price": stop})

        if current_r >= self.policy.partial_trigger_r and not bool(partial_taken):
            partial_qty = quantity * self.policy.partial_fraction
            partial = await self.execution.partial_close(
                position_id, market_price, partial_qty, "PROFIT_PARTIAL"
            )
            await self.database.execute(
                "UPDATE portfolio_positions SET partial_taken=1 WHERE id=?", (position_id,)
            )
            actions.append({"type": "PARTIAL_CLOSE", "reason": "PROFIT_PARTIAL", "result": partial})

        if current_r >= self.policy.trailing_start_r:
            trail = risk_per_unit * self.policy.trailing_distance_r
            candidate = highest - trail if side == "LONG" else lowest + trail
            improved = candidate > stop if side == "LONG" else candidate < stop
            if improved:
                stop = candidate
                await self.database.execute(
                    "UPDATE portfolio_positions SET stop_price=? WHERE id=?", (stop, position_id)
                )
                actions.append({"type": "MOVE_STOP", "reason": "R_TRAILING", "stop_price": stop})

        return self._result(position_id, symbol, current_r, stop, actions, False)

    async def evaluate_all(self, prices: dict[str, float]) -> dict[str, Any]:
        rows = await self.database.fetchall(
            "SELECT id, symbol FROM portfolio_positions WHERE status='OPEN' ORDER BY id"
        )
        results = []
        skipped = []
        for position_id, symbol in rows:
            price = prices.get(str(symbol))
            if price is None:
                skipped.append(str(symbol))
                continue
            results.append(await self.evaluate(int(position_id), float(price)))
        return {"evaluated": len(results), "skipped": skipped, "positions": results,
                "live_order_sent": False}

    @staticmethod
    def _result(position_id: int, symbol: str, current_r: float, stop: float,
                actions: list[dict[str, Any]], closed: bool) -> dict[str, Any]:
        return {
            "position_id": position_id,
            "symbol": str(symbol),
            "current_r": round(current_r, 6),
            "stop_price": round(stop, 12),
            "actions": actions,
            "closed": closed,
            "live_order_sent": False,
        }
