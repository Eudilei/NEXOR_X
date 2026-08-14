from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path.cwd()
REPORT_PATH = ROOT / "reports/final_runtime_integration_audit.json"

FORBIDDEN_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

REQUIRED_FILES = (
    "src/nexor_x/accounting/net_pnl.py",
    "src/nexor_x/accounting/runtime_integration.py",
    "src/nexor_x/operations/filter_rigidity.py",
    "src/nexor_x/operations/filter_decision_telemetry.py",
)


def read_text(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def check_file(rel: str) -> dict[str, Any]:
    exists = (ROOT / rel).exists()
    return {
        "name": f"file:{rel}",
        "passed": exists,
        "detail": "present" if exists else "missing",
    }


def find_token(token: str, files: list[str]) -> dict[str, Any]:
    matches = []
    for rel in files:
        text = read_text(rel)
        if token in text:
            matches.append(rel)

    return {
        "name": f"token:{token}",
        "passed": bool(matches),
        "detail": matches,
    }


def check_bankroll() -> dict[str, Any]:
    candidates = [
        ".env.example",
        "src/nexor_x/config.py",
        "src/nexor_x/settings.py",
        "src/nexor_x/config/settings.py",
    ]

    matches = []
    for rel in candidates:
        text = read_text(rel)
        if re.search(
            r"(INITIAL_BANKROLL\s*=\s*200(?:\.0+)?|"
            r"initial_bankroll\s*(?::\s*float)?\s*=\s*200(?:\.0+)?)",
            text,
        ):
            matches.append(rel)

    return {
        "name": "paper_bankroll_200",
        "passed": bool(matches),
        "detail": matches or "not found",
    }


def check_brl() -> dict[str, Any]:
    text = read_text(".env.example")
    passed = (
        "PAPER_BANKROLL_CURRENCY=BRL" in text
        or "NEXOR_PAPER_BANKROLL_CURRENCY=BRL" in text
    )
    return {
        "name": "paper_currency_brl",
        "passed": passed,
        "detail": "configured" if passed else "not found in .env.example",
    }


def check_fee_rates() -> dict[str, Any]:
    text = read_text(".env.example")
    maker = "NEXOR_PAPER_MAKER_FEE_RATE=" in text
    taker = "NEXOR_PAPER_TAKER_FEE_RATE=" in text
    return {
        "name": "paper_fee_rates_configurable",
        "passed": maker and taker,
        "detail": {
            "maker": maker,
            "taker": taker,
        },
    }


def check_api_endpoint(path_literal: str) -> dict[str, Any]:
    text = read_text("src/nexor_x/api/app.py")
    passed = path_literal in text
    return {
        "name": f"api:{path_literal}",
        "passed": passed,
        "detail": "present" if passed else "missing",
    }


def check_live_manifests() -> dict[str, Any]:
    suspicious = []

    for path in ROOT.rglob("update_manifest.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            suspicious.append({
                "path": str(path.relative_to(ROOT)),
                "reason": "invalid_json",
            })
            continue

        if data.get("live_execution_allowed") is not False:
            suspicious.append({
                "path": str(path.relative_to(ROOT)),
                "reason": "live_execution_allowed_not_false",
            })

    return {
        "name": "live_blocked_in_update_manifests",
        "passed": not suspicious,
        "detail": suspicious or "all discovered manifests keep LIVE blocked",
    }


def check_caches() -> dict[str, Any]:
    found = []

    for path in ROOT.rglob("*"):
        if path.is_dir() and path.name in FORBIDDEN_DIRS:
            found.append(str(path.relative_to(ROOT)))
        elif path.is_file() and path.suffix in {".pyc", ".pyo"}:
            found.append(str(path.relative_to(ROOT)))

    return {
        "name": "no_forbidden_caches",
        "passed": not found,
        "detail": found[:50] if found else "clean",
    }


def check_runtime_net_usage() -> dict[str, Any]:
    files = [
        "src/nexor_x/kernel.py",
        "src/nexor_x/trading/paper.py",
        "src/nexor_x/paper.py",
        "src/nexor_x/services/trading.py",
    ]

    adapter_refs = []
    normalization_refs = []
    net_refs = []

    for rel in files:
        text = read_text(rel)
        if not text:
            continue
        if "NetPnLRuntimeAdapter" in text:
            adapter_refs.append(rel)
        if "normalize_closed_trade(" in text:
            normalization_refs.append(rel)
        if "net_pnl" in text:
            net_refs.append(rel)

    passed = bool(adapter_refs and normalization_refs and net_refs)

    return {
        "name": "runtime_net_pnl_connected",
        "passed": passed,
        "detail": {
            "adapter_refs": adapter_refs,
            "normalize_closed_trade_refs": normalization_refs,
            "net_pnl_refs": net_refs,
        },
    }


def check_net_profit_factor() -> dict[str, Any]:
    files = [
        "src/nexor_x/accounting/runtime_integration.py",
        "src/nexor_x/kernel.py",
        "src/nexor_x/validation/evidence_certification.py",
        "src/nexor_x/operations/readiness_summary.py",
    ]

    matches = []
    for rel in files:
        text = read_text(rel)
        if (
            "NetPerformanceAggregator" in text
            or "pnl_basis" in text and "NET_AFTER_FEES" in text
        ):
            matches.append(rel)

    return {
        "name": "profit_factor_net_basis_present",
        "passed": bool(matches),
        "detail": matches or "not found",
    }


def main() -> int:
    checks: list[dict[str, Any]] = []

    for rel in REQUIRED_FILES:
        checks.append(check_file(rel))

    checks.extend([
        check_bankroll(),
        check_brl(),
        check_fee_rates(),
        find_token(
            "FilterRigidityMonitor",
            [
                "src/nexor_x/kernel.py",
                "src/nexor_x/operations/filter_rigidity.py",
            ],
        ),
        find_token(
            "FilterDecisionTelemetry",
            [
                "src/nexor_x/kernel.py",
                "src/nexor_x/operations/filter_decision_telemetry.py",
            ],
        ),
        check_api_endpoint("/api/operations/filter-rigidity"),
        check_api_endpoint("/api/operations/net-pnl-accounting"),
        check_runtime_net_usage(),
        check_net_profit_factor(),
        check_live_manifests(),
        check_caches(),
    ])

    failures = [item for item in checks if not item["passed"]]
    status = (
        "FINAL_RUNTIME_INTEGRATION_PASS"
        if not failures
        else "FINAL_RUNTIME_INTEGRATION_FAIL"
    )

    report = {
        "status": status,
        "passed": not failures,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failures),
        "checks_failed": len(failures),
        "failures": failures,
        "checks": checks,
        "live_allowed": False,
        "trading_logic_changed": False,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(status)
    print(
        f"checks={report['checks_passed']}/{report['checks_total']}"
    )

    if failures:
        print("Falhas:")
        for item in failures:
            print(f"- {item['name']}: {item['detail']}")

    print(f"Relatório: {REPORT_PATH}")
    print("LIVE: BLOQUEADO")

    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
