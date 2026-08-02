from pathlib import Path
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from nexor_x.api.app import create_app
from nexor_x.config import Settings
from nexor_x.kernel import Kernel


def test_probability_endpoint_exists(tmp_path: Path) -> None:
    kernel = Kernel(Settings(nexor_database_path=tmp_path / "test.db", _env_file=None))
    kernel.probability_assessment = AsyncMock(return_value={
        "symbol": "BTCUSDT", "decision": "LONG_BIAS", "raw_edge": 0.5,
        "regime": "TREND_UP", "ready": False, "method": "NONE",
        "sample_count": 0, "probability": None, "execution_allowed": False,
        "live_certified": False,
    })
    response = TestClient(create_app(kernel)).get("/api/probability/BTCUSDT")
    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_allowed"] is False
    assert payload["live_certified"] is False
