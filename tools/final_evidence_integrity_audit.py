
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


BUNDLE_PATH = Path("reports/final_evidence_bundle.json")
DIGEST_PATH = Path("reports/final_evidence_bundle.sha256")
REPORT_PATH = Path("reports/final_evidence_integrity_audit.json")


def _canonical_without_sha(payload: dict[str, Any]) -> bytes:
    clean = dict(payload)
    clean.pop("sha256", None)
    return json.dumps(
        clean,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} não contém objeto JSON")
    return payload


def audit(
    *,
    bundle_path: Path = BUNDLE_PATH,
    digest_path: Path = DIGEST_PATH,
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    details: dict[str, Any] = {}

    checks["bundle_exists"] = bundle_path.exists()
    checks["digest_exists"] = digest_path.exists()

    if not checks["bundle_exists"] or not checks["digest_exists"]:
        failed = [
            name for name, passed in checks.items() if not passed
        ]
        return {
            "status": "FINAL_EVIDENCE_INVALID",
            "verified": False,
            "checks": checks,
            "failed_checks": failed,
            "details": details,
            "live_allowed": False,
            "live_certified": False,
        }

    try:
        bundle = _load_json(bundle_path)
    except Exception as exc:
        checks["bundle_json_valid"] = False
        details["bundle_error"] = str(exc)
        bundle = {}
    else:
        checks["bundle_json_valid"] = True

    digest_line = digest_path.read_text(
        encoding="utf-8",
    ).strip()
    expected_digest = (
        digest_line.split()[0]
        if digest_line
        else ""
    )

    internal_digest = str(bundle.get("sha256", ""))
    calculated_digest = hashlib.sha256(
        _canonical_without_sha(bundle)
    ).hexdigest()

    checks["internal_sha256_valid"] = (
        len(internal_digest) == 64
        and internal_digest == calculated_digest
    )
    checks["digest_file_matches"] = (
        expected_digest == calculated_digest
    )

    checks["bundle_status_ready"] = (
        bundle.get("status") == "FINAL_EVIDENCE_READY"
    )

    requirements = bundle.get("requirements")
    if not isinstance(requirements, dict):
        requirements = {}

    checks["all_requirements_true"] = bool(requirements) and all(
        value is True
        for value in requirements.values()
    )

    checks["live_blocked"] = (
        bundle.get("live_allowed") is False
    )
    checks["live_not_certified"] = (
        bundle.get("live_certified") is False
    )

    rc = bundle.get("release_candidate")
    if not isinstance(rc, dict):
        rc = {}
    checks["release_candidate_ready"] = (
        rc.get("status") == "RC_READY"
        and rc.get("rc_ready") is True
    )

    completion = bundle.get("completion")
    if not isinstance(completion, dict):
        completion = {}
    checks["technical_completion"] = (
        completion.get("status") == "TECHNICALLY_COMPLETE"
        and completion.get("technically_complete") is True
    )

    campaign = bundle.get("campaign")
    if not isinstance(campaign, dict):
        campaign = {}
    checks["campaign_complete"] = (
        campaign.get("status") == "COMPLETE"
        and campaign.get("completed") is True
    )

    certification = bundle.get("certification")
    if not isinstance(certification, dict):
        certification = {}
    checks["evidence_certified"] = (
        certification.get("evidence_certified") is True
    )

    failed = [
        name
        for name, passed in checks.items()
        if not passed
    ]

    verified = not failed

    details.update(
        {
            "bundle_path": str(bundle_path),
            "digest_path": str(digest_path),
            "internal_sha256": internal_digest,
            "expected_sha256": expected_digest,
            "calculated_sha256": calculated_digest,
            "requirements": requirements,
        }
    )

    return {
        "status": (
            "FINAL_EVIDENCE_VERIFIED"
            if verified
            else "FINAL_EVIDENCE_INVALID"
        ),
        "verified": verified,
        "checks": checks,
        "failed_checks": failed,
        "details": details,
        "live_allowed": False,
        "live_certified": False,
    }


def main() -> int:
    result = audit()

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    REPORT_PATH.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(result["status"])
    print(f"Report: {REPORT_PATH}")

    if result["failed_checks"]:
        print("Falhas:")
        for item in result["failed_checks"]:
            print(f" - {item}")

    print("LIVE: BLOQUEADO")

    return 0 if result["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
