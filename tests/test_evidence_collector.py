from __future__ import annotations

import json

import pytest

from nexor_x.evidence import EvidenceCollector


class FakeDatabase:
    def __init__(self) -> None:
        self.tables = {
            "integration_health_reports": {
                "columns": {"id", "payload_json"},
                "rows": [
                    (
                        json.dumps(
                            {
                                "healthy": True,
                            }
                        ),
                    )
                ],
            },
            "recovery_reports": {
                "columns": {"id", "payload_json"},
                "rows": [
                    (
                        json.dumps(
                            {
                                "recovery_ok": True,
                            }
                        ),
                    )
                ],
            },
            "operational_supervisor_reports": {
                "columns": {"id", "payload_json"},
                "rows": [
                    (
                        json.dumps(
                            {
                                "paper_allowed": True,
                                "testnet_allowed": False,
                            }
                        ),
                    )
                ],
            },
        }

    async def fetchall(self, query, params=()):
        q = " ".join(str(query).split())

        if "sqlite_master" in q:
            name = params[0]
            return [(name,)] if name in self.tables else []

        if q.startswith("PRAGMA table_info("):
            table = q.split("(", 1)[1].split(")", 1)[0]
            cols = sorted(self.tables.get(table, {}).get("columns", set()))
            return [(index, name) for index, name in enumerate(cols)]

        for table, data in self.tables.items():
            if f"FROM {table}" in q:
                return data["rows"]

        return []


@pytest.mark.asyncio
async def test_missing_trade_tables_are_conservative() -> None:
    snapshot = await EvidenceCollector(FakeDatabase()).collect()
    assert snapshot.paper_trades == 0
    assert snapshot.profit_factor == 0.0
    assert snapshot.expected_r == 0.0
    assert snapshot.drawdown_pct == 100.0


@pytest.mark.asyncio
async def test_persisted_health_states_are_collected() -> None:
    snapshot = await EvidenceCollector(FakeDatabase()).collect()
    assert snapshot.integration_healthy is True
    assert snapshot.recovery_ok is True
    assert snapshot.supervisor_paper_allowed is True
    assert snapshot.supervisor_testnet_allowed is False


def test_snapshot_serializes() -> None:
    from nexor_x.evidence import EvidenceSnapshot

    snapshot = EvidenceSnapshot(
        paper_trades=1,
        profit_factor=1.2,
        expected_r=0.1,
        drawdown_pct=5.0,
        recent_profit_factor=1.1,
        recent_expected_r=0.05,
        operational_incidents=0,
        critical_test_failures=0,
        integration_healthy=True,
        recovery_ok=True,
        supervisor_paper_allowed=True,
        supervisor_testnet_allowed=True,
    )
    assert snapshot.to_dict()["paper_trades"] == 1
