
import importlib.util
import json
from pathlib import Path


def load_module():
    path = (
        Path(__file__).parents[1]
        / "tools"
        / "validation_campaign_runner.py"
    )
    spec = importlib.util.spec_from_file_location(
        "validation_campaign_runner",
        path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_cycle_calls_only_validation_endpoints(tmp_path):
    module = load_module()
    runner = module.ValidationCampaignRunner(
        base_url="http://example.invalid",
        admin_token="test",
        report_dir=tmp_path,
    )

    calls = []

    def fake_call(path, *, method):
        calls.append((path, method))
        if path.endswith("/tick"):
            return {
                "sample_reason": "PASS_RECORDED",
            }
        if path.endswith("/final-snapshot"):
            return {
                "status": "VALIDATION_PENDING",
                "validation_progress_percent": 5.0,
                "live_allowed": False,
            }
        return {
            "status": "RC_READY",
            "live_allowed": False,
        }

    runner._call = fake_call
    result = runner.cycle()

    assert calls == [
        ("/api/validation/final-campaign/tick", "POST"),
        ("/api/validation/final-snapshot", "GET"),
        ("/api/validation/release-candidate", "GET"),
    ]
    assert result["live_allowed"] is False


def test_cycle_persists_history_and_latest(tmp_path):
    module = load_module()
    runner = module.ValidationCampaignRunner(
        base_url="http://example.invalid",
        admin_token="test",
        report_dir=tmp_path,
    )
    runner._call = lambda path, method: {
        "status": "PASS",
        "live_allowed": False,
    }

    runner.cycle()

    history = tmp_path / "validation_campaign_history.jsonl"
    latest = tmp_path / "validation_campaign_latest.json"

    assert history.exists()
    assert latest.exists()

    lines = history.read_text(
        encoding="utf-8",
    ).strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["live_allowed"] is False


def test_runner_contains_no_order_endpoint():
    module = load_module()
    source = Path(module.__file__).read_text(
        encoding="utf-8",
    ).lower()

    forbidden = (
        "/order",
        "/orders",
        "paper_open",
        "testnet_order_create",
    )

    assert all(token not in source for token in forbidden)
