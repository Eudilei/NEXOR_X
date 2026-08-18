from __future__ import annotations

from datetime import UTC, datetime

from nexor_x.infrastructure.database import DatabaseService


class PortfolioService:
    """Read-only portfolio state used by the pre-trade gate.

    Sprint 7 deliberately does not create orders. It centralizes equity, peak equity,
    drawdown and exposure so later execution code cannot invent its own risk state.
    """

    def __init__(self, database: DatabaseService, initial_equity: float) -> None:
        if initial_equity <= 0:
            raise ValueError("initial_equity must be positive")
        self.database = database
        self.initial_equity = float(initial_equity)

    async def ensure_account(self) -> None:
        now = datetime.now(UTC).isoformat()
        await self.database.execute(
            """INSERT OR IGNORE INTO portfolio_accounts
            (account_id, equity, peak_equity, realized_pnl, updated_at)
            VALUES ('PAPER', ?, ?, 0.0, ?)""",
            (self.initial_equity, self.initial_equity, now),
        )

    async def snapshot(self) -> dict[str, object]:
        await self.ensure_account()
        rows = await self.database.fetchall(
            """SELECT equity, peak_equity, realized_pnl, updated_at
            FROM portfolio_accounts WHERE account_id='PAPER'"""
        )
        equity, peak, realized, updated_at = rows[0]
        position_rows = await self.database.fetchall(
            """SELECT COUNT(*), COALESCE(SUM(notional), 0.0)
            FROM portfolio_positions WHERE status='OPEN'"""
        )
        open_positions, gross_notional = position_rows[0]
        equity_f = float(equity)
        peak_f = max(float(peak), equity_f)
        drawdown = 0.0 if peak_f <= 0 else max(0.0, (peak_f - equity_f) / peak_f)
        positions = await self.database.fetchall(
            """SELECT id, symbol, side, quantity, entry_price, notional, stop_price, opened_at
            FROM portfolio_positions WHERE status='OPEN' ORDER BY opened_at"""
        )
        open_risk_brl = sum(
            abs(float(r[4]) - float(r[6])) * float(r[3])
            for r in positions if r[6] is not None
        )
        return {
            "account_id": "PAPER",
            "equity": round(equity_f, 8),
            "peak_equity": round(peak_f, 8),
            "realized_pnl": round(float(realized), 8),
            "drawdown_pct": round(drawdown * 100.0, 6),
            "open_positions": int(open_positions),
            "gross_notional": round(float(gross_notional), 8),
            "open_risk_brl": round(open_risk_brl, 8),
            "open_risk_pct": round(open_risk_brl/equity_f*100.0, 6) if equity_f > 0 else 100.0,
            "positions": [
                {"id": int(r[0]), "symbol": str(r[1]), "side": str(r[2]),
                 "quantity": float(r[3]), "entry_price": float(r[4]),
                 "notional": float(r[5]), "stop_price": None if r[6] is None else float(r[6]), "opened_at": str(r[7])}
                for r in positions
            ],
            "updated_at": str(updated_at),
        }
