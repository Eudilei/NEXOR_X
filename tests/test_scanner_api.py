from pathlib import Path
from fastapi.testclient import TestClient
from nexor_x.api.app import create_app
from nexor_x.config import Settings
from nexor_x.kernel import Kernel


def test_scanner_status_endpoint_exists(tmp_path: Path) -> None:
    settings = Settings(nexor_database_path=tmp_path / "test.db", _env_file=None)
    kernel = Kernel(settings)
    client = TestClient(create_app(kernel))
    response = client.get("/api/scanner/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_triggered"] is False
    assert "BTCUSDT" in payload["configured_symbols"]
