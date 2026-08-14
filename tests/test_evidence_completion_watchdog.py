
import importlib.util
import json
from pathlib import Path


def load_module():
    path = (
        Path(__file__).parents[1]
        / "tools"
        / "evidence_completion_watchdog.py"
    )
    spec = importlib.util.spec_from_file_location(
        "evidence_completion_watchdog",
        path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def ready_payload(path):
    if path.endswith("/certification"):
        return {
            "candidate_ready": True,
            "evidence_certified": True,
            "live_allowed": False,
        }
    if path.endswith("/final-campaign"):
        return {
            "status": "COMPLETE",
            "completed": True,
            "live_allowed": False,
        }
    if path.endswith("/final-completion"):
        return {
            "status": "TECHNICALLY_COMPLETE",
            "technically_complete": True,
            "candidate_ready": True,
            "evidence_certified": True,
            "live_allowed": False,
        }
    return {
        "status": "RC_READY",
        "rc_ready": True,
        "live_allowed": False,
    }


def test_ready_generates_bundle(tmp_path):
    module = load_module()
    w = module.EvidenceCompletionWatchdog(
        base_url="http://example.invalid",
        admin_token="test",
        report_dir=tmp_path,
    )
    w._get = ready_payload

    report = w.evaluate()

    assert report["status"] == "FINAL_EVIDENCE_READY"
    assert report["final_evidence_ready"] is True
    assert report["live_allowed"] is False

    bundle = tmp_path / "final_evidence_bundle.json"
    digest = tmp_path / "final_evidence_bundle.sha256"

    assert bundle.exists()
    assert digest.exists()

    payload = json.loads(bundle.read_text(encoding="utf-8"))
    assert len(payload["sha256"]) == 64
    assert payload["live_allowed"] is False


def test_pending_does_not_generate_bundle(tmp_path):
    module = load_module()
    w = module.EvidenceCompletionWatchdog(
        base_url="http://example.invalid",
        admin_token="test",
        report_dir=tmp_path,
    )

    def fake(path):
        payload = ready_payload(path)
        if path.endswith("/certification"):
            payload["evidence_certified"] = False
        return payload

    w._get = fake
    report = w.evaluate()

    assert report["status"] == "EVIDENCE_PENDING"
    assert "evidence_certified" in report["pending_requirements"]
    assert not (tmp_path / "final_evidence_bundle.json").exists()


def test_watchdog_only_uses_get_endpoints():
    module = load_module()
    source = Path(module.__file__).read_text(
        encoding="utf-8",
    ).lower()

    forbidden = (
        'method="post"',
        "paper_open",
        "testnet_order_create",
        "/order",
        "/orders",
    )

    assert all(token not in source for token in forbidden)
