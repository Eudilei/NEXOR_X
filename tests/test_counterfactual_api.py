from types import SimpleNamespace

from fastapi.testclient import TestClient

from nexor_x.api.app import create_app


class KernelStub:
    def __init__(self):
        self.settings = SimpleNamespace(admin_api_token="secret")

    async def counterfactual_status(self):
        return {"status": "NOT_RUN", "execution_allowed": False}

    async def run_counterfactual(self, **kwargs):
        return {"status": "NO_IMPROVEMENT", "causal_claim": False, "kwargs": kwargs}


def test_counterfactual_run_requires_admin():
    client = TestClient(create_app(KernelStub()))
    response = client.post("/api/counterfactual/run", json={})
    assert response.status_code == 401
    ok = client.post(
        "/api/counterfactual/run", json={}, headers={"X-NEXOR-ADMIN-TOKEN": "secret"}
    )
    assert ok.status_code == 200
    assert ok.json()["causal_claim"] is False
