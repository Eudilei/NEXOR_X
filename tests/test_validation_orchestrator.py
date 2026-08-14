
import importlib.util
import json
from pathlib import Path


def load_module():
    path = (
        Path(__file__).parents[1]
        / "tools"
        / "validation_orchestrator.py"
    )
    spec = importlib.util.spec_from_file_location(
        "validation_orchestrator",
        path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_cycle_orders_validation_tools(tmp_path, monkeypatch):
    module = load_module()

    reports = tmp_path / "reports"
    reports.mkdir()

    monkeypatch.setattr(
        module,
        "HEARTBEAT_PATH",
        reports / "heartbeat.json",
    )
    monkeypatch.setattr(
        module,
        "HISTORY_PATH",
        reports / "history.jsonl",
    )

    o = module.ValidationOrchestrator(repo=tmp_path)

    calls = []

    def fake_run(name, relative_path, *, args=None, acceptable_codes):
        calls.append(name)
        return {
            "name": name,
            "status": "OK",
            "returncode": 0,
        }

    o._run_tool = fake_run
    report = o.run_cycle()

    assert calls[:4] == [
        "rc_verify",
        "validation_campaign",
        "evidence_progress",
        "evidence_watchdog",
    ]
    assert report["status"] == "ORCHESTRATOR_OK"
    assert report["live_allowed"] is False


def test_integrity_and_preauth_skipped_without_bundle(tmp_path, monkeypatch):
    module = load_module()
    reports = tmp_path / "reports"
    reports.mkdir()

    monkeypatch.setattr(
        module,
        "HEARTBEAT_PATH",
        reports / "heartbeat.json",
    )
    monkeypatch.setattr(
        module,
        "HISTORY_PATH",
        reports / "history.jsonl",
    )

    o = module.ValidationOrchestrator(repo=tmp_path)

    def fake_run(name, relative_path, *, args=None, acceptable_codes):
        return {
            "name": name,
            "status": "OK",
            "returncode": 0,
        }

    o._run_tool = fake_run
    report = o.run_cycle()

    statuses = {
        step["name"]: step["status"]
        for step in report["steps"]
    }

    assert statuses["evidence_integrity"] == "SKIPPED"
    assert statuses["live_preauthorization"] == "SKIPPED"


def test_verified_integrity_enables_only_preauth_check(tmp_path, monkeypatch):
    module = load_module()
    reports = tmp_path / "reports"
    reports.mkdir()

    monkeypatch.setattr(
        module,
        "HEARTBEAT_PATH",
        reports / "heartbeat.json",
    )
    monkeypatch.setattr(
        module,
        "HISTORY_PATH",
        reports / "history.jsonl",
    )

    (reports / "final_evidence_bundle.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (
        reports
        / "final_evidence_integrity_audit.json"
    ).write_text(
        json.dumps({
            "status": "FINAL_EVIDENCE_VERIFIED",
            "verified": True,
        }),
        encoding="utf-8",
    )

    o = module.ValidationOrchestrator(repo=tmp_path)
    calls = []

    def fake_run(name, relative_path, *, args=None, acceptable_codes):
        calls.append(name)
        return {
            "name": name,
            "status": "OK",
            "returncode": 0,
        }

    o._run_tool = fake_run
    report = o.run_cycle()

    assert "evidence_integrity" in calls
    assert "live_preauthorization" in calls
    assert report["trading_runtime_changed"] is False


def test_lock_releases(tmp_path):
    module = load_module()
    lock_path = tmp_path / "orchestrator.lock"

    lock = module.InstanceLock(path=lock_path)
    lock.acquire()
    assert lock_path.exists()

    lock.release()
    assert not lock_path.exists()


def test_orchestrator_has_no_order_execution_markers():
    module = load_module()
    source = Path(module.__file__).read_text(
        encoding="utf-8",
    ).lower()

    forbidden = (
        "paper_open(",
        "testnet_order_create(",
        "/api/order",
        "/api/orders",
        'live_allowed": true',
    )

    assert all(token not in source for token in forbidden)
