import importlib.util
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "final_runtime_integration_audit.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "final_runtime_integration_audit",
        MODULE_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_required_files_list_contains_net_accounting() -> None:
    module = load_module()
    assert "src/nexor_x/accounting/net_pnl.py" in module.REQUIRED_FILES
    assert (
        "src/nexor_x/accounting/runtime_integration.py"
        in module.REQUIRED_FILES
    )


def test_required_files_list_contains_filter_telemetry() -> None:
    module = load_module()
    assert (
        "src/nexor_x/operations/filter_rigidity.py"
        in module.REQUIRED_FILES
    )
    assert (
        "src/nexor_x/operations/filter_decision_telemetry.py"
        in module.REQUIRED_FILES
    )


def test_forbidden_cache_policy() -> None:
    module = load_module()
    assert "__pycache__" in module.FORBIDDEN_DIRS
    assert ".pytest_cache" in module.FORBIDDEN_DIRS


def test_report_contract_is_live_blocked(tmp_path, monkeypatch) -> None:
    module = load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(
        module,
        "REPORT_PATH",
        tmp_path / "reports" / "final_runtime_integration_audit.json",
    )

    # Empty repo should fail, but must never enable LIVE.
    code = module.main()
    assert code == 1

    import json
    report = json.loads(
        module.REPORT_PATH.read_text(encoding="utf-8")
    )
    assert report["live_allowed"] is False
    assert report["trading_logic_changed"] is False
