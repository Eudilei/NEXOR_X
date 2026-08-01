from pathlib import Path
from fastapi.testclient import TestClient
from nexor_x.api.app import create_app
from nexor_x.config import Settings
from nexor_x.kernel import Kernel

def test_command_center_loads(tmp_path: Path) -> None:
    settings = Settings(nexor_database_path=tmp_path / "test.db", _env_file=None)
    client = TestClient(create_app(Kernel(settings)))
    response = client.get("/")
    assert response.status_code == 200
    assert "NEXOR X" in response.text
