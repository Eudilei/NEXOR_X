from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nexor_x.api.app import create_app
from nexor_x.config import Settings
from nexor_x.infrastructure.database import DatabaseService
from nexor_x.kernel import Kernel


def test_admin_endpoint_requires_configured_token(tmp_path: Path) -> None:
    settings = Settings(nexor_database_path=tmp_path / "x.db", admin_api_token="", _env_file=None)
    client = TestClient(create_app(Kernel(settings)))
    response = client.post("/api/scanner/run")
    assert response.status_code == 503


def test_admin_endpoint_rejects_wrong_token(tmp_path: Path) -> None:
    settings = Settings(
        nexor_database_path=tmp_path / "x.db", admin_api_token="correct", _env_file=None
    )
    client = TestClient(create_app(Kernel(settings)))
    response = client.post("/api/scanner/run", headers={"X-NEXOR-ADMIN-TOKEN": "wrong"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_database_transaction_rolls_back_all_statements(tmp_path: Path) -> None:
    db = DatabaseService(tmp_path / "x.db")
    await db.start()
    await db.execute(
        "INSERT INTO portfolio_accounts(account_id,equity,peak_equity,realized_pnl,updated_at) VALUES('PAPER',100,100,0,'now')"
    )
    with pytest.raises(Exception):
        await db.transaction(
            [
                ("UPDATE portfolio_accounts SET equity=90 WHERE account_id='PAPER'", ()),
                ("INSERT INTO table_that_does_not_exist(value) VALUES(?)", (1,)),
            ]
        )
    rows = await db.fetchall("SELECT equity FROM portfolio_accounts WHERE account_id='PAPER'")
    assert rows == [(100.0,)]
    await db.stop()
