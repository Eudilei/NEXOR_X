
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import Any


EXPECTED_VERSION = "0.57.0"

REQUIRED_FILES = (
    "src/nexor_x/operations/degradation.py",
    "src/nexor_x/operations/entry_admission.py",
    "src/nexor_x/operations/recovery_hysteresis.py",
    "src/nexor_x/operations/post_recovery_probation.py",
    "src/nexor_x/operations/probation_exposure_ramp.py",
    "src/nexor_x/operations/entry_reservation.py",
    "src/nexor_x/operations/entry_decision_trace.py",
    "src/nexor_x/operations/operational_readiness_summary.py",
    "src/nexor_x/operations/operational_acceptance_audit.py",
    "src/nexor_x/validation/final_campaign.py",
    "src/nexor_x/validation/final_completion.py",
    "src/nexor_x/validation/final_dashboard.py",
    "src/nexor_x/validation/release_candidate.py",
    "docs/NEXOR_X_RELEASE_CANDIDATE.md",
)

REQUIRED_ENDPOINT_MARKERS = (
    '/api/operations/degradation',
    '/api/operations/entry-admission',
    '/api/operations/recovery-hysteresis',
    '/api/operations/post-recovery-probation',
    '/api/operations/exposure-ramp',
    '/api/operations/entry-reservation',
    '/api/operations/entry-decision-trace',
    '/api/operations/readiness-summary',
    '/api/operations/acceptance-audit',
    '/api/validation/final-campaign',
    '/api/validation/final-completion',
    '/api/validation/final-snapshot',
    '/api/validation/release-candidate',
)

FORBIDDEN_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

FORBIDDEN_SUFFIXES = {".pyc", ".pyo"}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def verify(repo: Path) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    details: dict[str, Any] = {}

    pyproject = repo / "pyproject.toml"
    init_file = repo / "src/nexor_x/__init__.py"
    api_file = repo / "src/nexor_x/api/app.py"

    pyproject_text = _read(pyproject) if pyproject.exists() else ""
    init_text = _read(init_file) if init_file.exists() else ""
    api_text = _read(api_file) if api_file.exists() else ""

    checks["pyproject_version"] = (
        f'version = "{EXPECTED_VERSION}"' in pyproject_text
    )
    checks["package_version"] = (
        f'__version__ = "{EXPECTED_VERSION}"' in init_text
    )

    missing_files = [
        rel
        for rel in REQUIRED_FILES
        if not (repo / rel).exists()
    ]
    checks["critical_files_present"] = not missing_files
    details["missing_files"] = missing_files

    missing_endpoints = [
        marker
        for marker in REQUIRED_ENDPOINT_MARKERS
        if marker not in api_text
    ]
    checks["final_endpoints_present"] = not missing_endpoints
    details["missing_endpoints"] = missing_endpoints

    blocked_artifacts: list[str] = []
    for path in repo.rglob("*"):
        rel = path.relative_to(repo)
        if any(part in FORBIDDEN_PARTS for part in rel.parts):
            blocked_artifacts.append(str(rel))
            continue
        if path.suffix in FORBIDDEN_SUFFIXES:
            blocked_artifacts.append(str(rel))

    checks["no_forbidden_artifacts"] = not blocked_artifacts
    details["forbidden_artifacts"] = blocked_artifacts[:50]

    manifests = list(repo.glob("NEXOR_X_UPDATE_*/update_manifest.json"))
    live_manifest_violations: list[str] = []
    for path in manifests:
        try:
            payload = json.loads(_read(path))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("live_execution_allowed") is not False:
            live_manifest_violations.append(str(path.relative_to(repo)))

    checks["update_manifests_keep_live_blocked"] = (
        not live_manifest_violations
    )
    details["live_manifest_violations"] = live_manifest_violations

    runtime_live_markers = [
        "live_allowed = True",
        '"live_allowed": True',
        "'live_allowed': True",
        "live_execution_allowed = True",
    ]
    suspicious_live_lines: list[str] = []

    for rel in (
        "src/nexor_x/operations",
        "src/nexor_x/validation",
    ):
        base = repo / rel
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            text = _read(path)
            for marker in runtime_live_markers:
                if marker in text:
                    suspicious_live_lines.append(
                        f"{path.relative_to(repo)} :: {marker}"
                    )

    checks["no_live_true_in_rc_gates"] = not suspicious_live_lines
    details["suspicious_live_markers"] = suspicious_live_lines

    rc_doc = repo / "docs/NEXOR_X_RELEASE_CANDIDATE.md"
    checks["release_candidate_documented"] = rc_doc.exists()

    failed = [
        name
        for name, passed in checks.items()
        if not passed
    ]

    return {
        "status": "RC_VERIFY_PASS" if not failed else "RC_VERIFY_FAIL",
        "passed": not failed,
        "expected_version": EXPECTED_VERSION,
        "checks": checks,
        "failed_checks": failed,
        "details": details,
        "live_allowed": False,
    }


def main() -> int:
    repo = Path.cwd()
    report = verify(repo)

    report_dir = repo / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "rc_verification_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(report["status"])
    print(f"Report: {report_path}")

    if report["failed_checks"]:
        print("Failed checks:")
        for item in report["failed_checks"]:
            print(f" - {item}")

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
