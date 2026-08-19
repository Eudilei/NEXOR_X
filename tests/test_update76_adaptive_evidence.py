from pathlib import Path

import pytest

from nexor_x.evidence import EvidenceCollector
from nexor_x.infrastructure.database import DatabaseService
from nexor_x.operations.performance_degradation import PerformanceDegradationGuard


@pytest.mark.asyncio
async def test_closed_portfolio_positions_feed_adaptive_protection(tmp_path: Path) -> None:
    database = DatabaseService(tmp_path / "update76.db")
    await database.start()
    try:
        await database.execute(
            "INSERT INTO portfolio_accounts "
            "(account_id,equity,peak_equity,realized_pnl,updated_at) "
            "VALUES ('PAPER',180,200,-20,'2026-08-19T00:00:00Z')"
        )
        for index in range(6):
            await database.execute(
                "INSERT INTO portfolio_positions "
                "(symbol,side,quantity,entry_price,notional,status,opened_at,"
                "closed_at,realized_pnl) VALUES (?,?,?,?,?,'CLOSED',?,?,?)",
                (f"T{index}USDT", "LONG", 1.0, 10.0, 10.0,
                 "2026-08-19T00:00:00Z", "2026-08-19T01:00:00Z", -1.0),
            )
        evidence = await EvidenceCollector(database).collect()
        assert evidence.paper_trades == 6
        assert evidence.recent_trades == 6
        assert evidence.loss_streak == 6
        assert evidence.drawdown_pct == pytest.approx(10.0)
        report = PerformanceDegradationGuard().evaluate(
            recent=evidence.to_dict(), certification={"evidence_certified": True}
        )
        assert report["state"] == "BLOCKED"
        assert "loss_streak_critical" in report["hard_reasons"]
    finally:
        await database.stop()


def test_guard_accepts_paper_trade_count_from_evidence() -> None:
    report = PerformanceDegradationGuard().evaluate(
        recent={"paper_trades": 25, "recent_profit_factor": 0.9,
                "drawdown_pct": 5.0, "loss_streak": 1},
        certification={"evidence_certified": True},
    )
    assert report["metrics"]["enough_sample"] is True
    assert report["new_entries_allowed"] is False
