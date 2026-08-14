
import hashlib
import importlib.util
import json
from pathlib import Path


def load_module():
    path = (
        Path(__file__).parents[1]
        / "tools"
        / "final_evidence_integrity_audit.py"
    )
    spec = importlib.util.spec_from_file_location(
        "final_evidence_integrity_audit",
        path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def ready_bundle():
    return {
        "bundle_type": "NEXOR_X_FINAL_EVIDENCE",
        "bundle_version": 1,
        "created_at": "2026-08-13T20:00:00+00:00",
        "status": "FINAL_EVIDENCE_READY",
        "requirements": {
            "release_candidate_ready": True,
            "technical_completion": True,
            "validation_campaign_complete": True,
            "candidate_ready": True,
            "evidence_certified": True,
            "live_still_blocked": True,
        },
        "certification": {
            "evidence_certified": True,
            "live_allowed": False,
        },
        "campaign": {
            "status": "COMPLETE",
            "completed": True,
            "live_allowed": False,
        },
        "completion": {
            "status": "TECHNICALLY_COMPLETE",
            "technically_complete": True,
            "live_allowed": False,
        },
        "release_candidate": {
            "status": "RC_READY",
            "rc_ready": True,
            "live_allowed": False,
        },
        "live_allowed": False,
        "live_certified": False,
    }


def write_bundle(tmp_path, module):
    bundle = ready_bundle()
    canonical = json.dumps(
        bundle,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    bundle["sha256"] = digest

    bundle_path = tmp_path / "final_evidence_bundle.json"
    digest_path = tmp_path / "final_evidence_bundle.sha256"

    bundle_path.write_text(
        json.dumps(bundle, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    digest_path.write_text(
        f"{digest}  final_evidence_bundle.json\n",
        encoding="utf-8",
    )
    return bundle_path, digest_path


def test_valid_bundle_is_verified(tmp_path):
    module = load_module()
    bundle_path, digest_path = write_bundle(tmp_path, module)

    report = module.audit(
        bundle_path=bundle_path,
        digest_path=digest_path,
    )

    assert report["status"] == "FINAL_EVIDENCE_VERIFIED"
    assert report["verified"] is True
    assert report["live_allowed"] is False


def test_tampered_bundle_fails_hash(tmp_path):
    module = load_module()
    bundle_path, digest_path = write_bundle(tmp_path, module)

    payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    payload["campaign"]["completed"] = False
    bundle_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    report = module.audit(
        bundle_path=bundle_path,
        digest_path=digest_path,
    )

    assert report["verified"] is False
    assert (
        "internal_sha256_valid" in report["failed_checks"]
        or "digest_file_matches" in report["failed_checks"]
    )


def test_live_true_invalidates_bundle(tmp_path):
    module = load_module()
    bundle = ready_bundle()
    bundle["live_allowed"] = True

    canonical = json.dumps(
        bundle,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    bundle["sha256"] = digest

    bundle_path = tmp_path / "final_evidence_bundle.json"
    digest_path = tmp_path / "final_evidence_bundle.sha256"

    bundle_path.write_text(
        json.dumps(bundle, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    digest_path.write_text(
        f"{digest}  final_evidence_bundle.json\n",
        encoding="utf-8",
    )

    report = module.audit(
        bundle_path=bundle_path,
        digest_path=digest_path,
    )

    assert report["verified"] is False
    assert "live_blocked" in report["failed_checks"]


def test_missing_bundle_is_invalid(tmp_path):
    module = load_module()

    report = module.audit(
        bundle_path=tmp_path / "missing.json",
        digest_path=tmp_path / "missing.sha256",
    )

    assert report["status"] == "FINAL_EVIDENCE_INVALID"
    assert report["verified"] is False
