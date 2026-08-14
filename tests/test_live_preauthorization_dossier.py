
import importlib.util
from pathlib import Path


def load_module():
    path = (
        Path(__file__).parents[1]
        / "tools"
        / "live_preauthorization_dossier.py"
    )
    spec = importlib.util.spec_from_file_location(
        "live_preauthorization_dossier",
        path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def good_integrity():
    return {
        "status": "FINAL_EVIDENCE_VERIFIED",
        "verified": True,
        "live_allowed": False,
        "live_certified": False,
    }


def good_env():
    return {
        "NEXOR_MODE": "PAPER",
        "BINANCE_API_KEY": "key-value",
        "BINANCE_API_SECRET": "secret-value",
        "TELEGRAM_BOT_TOKEN": "bot-token",
        "TELEGRAM_CHAT_ID": "123",
    }


def test_ready_when_all_checks_pass():
    module = load_module()
    report = module.build_dossier(
        integrity_report=good_integrity(),
        env=good_env(),
    )

    assert report["status"] == "LIVE_PREAUTH_READY"
    assert report["preauthorization_ready"] is True
    assert report["live_allowed"] is False
    assert report["secret_values_included"] is False


def test_live_mode_blocks_preauthorization():
    module = load_module()
    env = good_env()
    env["NEXOR_MODE"] = "LIVE"

    report = module.build_dossier(
        integrity_report=good_integrity(),
        env=env,
    )

    assert report["status"] == "LIVE_PREAUTH_BLOCKED"
    assert "runtime_not_live" in report["failed_checks"]


def test_missing_secret_blocks_without_exposing_value():
    module = load_module()
    env = good_env()
    env["BINANCE_API_SECRET"] = ""

    report = module.build_dossier(
        integrity_report=good_integrity(),
        env=env,
    )

    assert report["preauthorization_ready"] is False
    assert "binance_api_secret_present" in report["failed_checks"]
    assert "secret-value" not in str(report)


def test_unverified_evidence_blocks():
    module = load_module()
    integrity = good_integrity()
    integrity["verified"] = False

    report = module.build_dossier(
        integrity_report=integrity,
        env=good_env(),
    )

    assert report["status"] == "LIVE_PREAUTH_BLOCKED"
    assert "final_evidence_verified" in report["failed_checks"]


def test_tool_contains_no_runtime_live_activation():
    module = load_module()
    source = Path(module.__file__).read_text(
        encoding="utf-8",
    ).lower()

    forbidden = (
        "paper_open",
        "testnet_order_create",
        'live_allowed": true',
        "live_execution_allowed = true",
        "/api/order",
        "/api/orders",
    )

    assert all(token not in source for token in forbidden)
