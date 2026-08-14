
import importlib.util
import json
from pathlib import Path


def load_module():
    path = (
        Path(__file__).parents[1]
        / "tools"
        / "evidence_progress_recorder.py"
    )
    spec = importlib.util.spec_from_file_location(
        "evidence_progress_recorder",
        path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_collect_uses_only_read_endpoints(tmp_path):
    module = load_module()
    recorder = module.EvidenceProgressRecorder(
        base_url="http://example.invalid",
        admin_token="test",
        report_dir=tmp_path,
    )

    calls = []

    def fake_get(path):
        calls.append(path)
        if path.endswith("/certification"):
            return {
                "evidence_certified": False,
                "metrics": {
                    "closed_trades": 12,
                    "profit_factor": 1.31,
                },
                "blockers": ["min_closed_trades"],
            }
        if path.endswith("/final-snapshot"):
            return {
                "candidate_ready": True,
                "validation_status": "IN_PROGRESS",
                "validation_progress_percent": 30.0,
                "validation_passes": 6,
                "validation_required_passes": 20,
                "blockers": [],
            }
        return {
            "status": "RC_READY",
        }

    recorder._get = fake_get
    result = recorder.collect()

    assert calls == list(module.EvidenceProgressRecorder.ENDPOINTS)
    assert result["summary"]["validation_passes"] == 6
    assert result["summary"]["metrics"]["closed_trades"] == 12
    assert result["live_allowed"] is False


def test_persists_history_and_latest(tmp_path):
    module = load_module()
    recorder = module.EvidenceProgressRecorder(
        base_url="http://example.invalid",
        admin_token="test",
        report_dir=tmp_path,
    )
    recorder._get = lambda path: {}

    recorder.collect()

    history = tmp_path / "evidence_progress_history.jsonl"
    latest = tmp_path / "evidence_progress_latest.json"

    assert history.exists()
    assert latest.exists()

    lines = history.read_text(
        encoding="utf-8",
    ).strip().splitlines()

    assert len(lines) == 1
    assert json.loads(lines[0])["live_allowed"] is False


def test_recorder_contains_no_order_or_write_endpoint():
    module = load_module()
    source = Path(module.__file__).read_text(
        encoding="utf-8",
    ).lower()

    forbidden = (
        "paper_open",
        "testnet_order_create",
        'method="post"',
        "/order",
        "/orders",
    )

    assert all(token not in source for token in forbidden)
