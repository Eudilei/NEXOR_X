
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


INTEGRITY_REPORT = Path(
    "reports/final_evidence_integrity_audit.json"
)
OUTPUT_REPORT = Path(
    "reports/live_preauthorization_dossier.json"
)

REQUIRED_ENV = (
    "BINANCE_API_KEY",
    "BINANCE_API_SECRET",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
)


def _load_integrity_report(
    path: Path = INTEGRITY_REPORT,
) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Integrity report inválido")
    return payload


def build_dossier(
    *,
    integrity_report: dict[str, Any],
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    env_map = dict(os.environ if env is None else env)

    mode = str(
        env_map.get("NEXOR_MODE", "PAPER")
    ).strip().upper()

    credentials_present = {
        name: bool(
            str(env_map.get(name, "")).strip()
        )
        for name in REQUIRED_ENV
    }

    checks = {
        "final_evidence_verified": (
            integrity_report.get("status")
            == "FINAL_EVIDENCE_VERIFIED"
            and integrity_report.get("verified") is True
        ),
        "runtime_not_live": mode != "LIVE",
        "binance_api_key_present": credentials_present[
            "BINANCE_API_KEY"
        ],
        "binance_api_secret_present": credentials_present[
            "BINANCE_API_SECRET"
        ],
        "telegram_bot_token_present": credentials_present[
            "TELEGRAM_BOT_TOKEN"
        ],
        "telegram_chat_id_present": credentials_present[
            "TELEGRAM_CHAT_ID"
        ],
    }

    failed = [
        name
        for name, passed in checks.items()
        if not passed
    ]

    ready = not failed

    return {
        "status": (
            "LIVE_PREAUTH_READY"
            if ready
            else "LIVE_PREAUTH_BLOCKED"
        ),
        "preauthorization_ready": ready,
        "checks": checks,
        "failed_checks": failed,
        "runtime_mode": mode,
        "configured_fields": credentials_present,
        "secret_values_included": False,
        "live_allowed": False,
        "live_certified": False,
        "runtime_change_performed": False,
        "next_step": (
            "Explicit operator authorization remains required."
            if ready
            else "Resolve failed checks before any LIVE discussion."
        ),
    }


def main() -> int:
    if not INTEGRITY_REPORT.exists():
        result = {
            "status": "LIVE_PREAUTH_BLOCKED",
            "preauthorization_ready": False,
            "checks": {
                "final_evidence_verified": False,
            },
            "failed_checks": [
                "final_evidence_verified",
            ],
            "reason": (
                "Execute primeiro "
                "tools/final_evidence_integrity_audit.py"
            ),
            "secret_values_included": False,
            "live_allowed": False,
            "live_certified": False,
            "runtime_change_performed": False,
        }
    else:
        try:
            integrity = _load_integrity_report()
            result = build_dossier(
                integrity_report=integrity,
            )
        except Exception as exc:
            result = {
                "status": "LIVE_PREAUTH_BLOCKED",
                "preauthorization_ready": False,
                "failed_checks": [
                    "integrity_report_read",
                ],
                "reason": str(exc),
                "secret_values_included": False,
                "live_allowed": False,
                "live_certified": False,
                "runtime_change_performed": False,
            }

    OUTPUT_REPORT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    OUTPUT_REPORT.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(result["status"])
    print(f"Report: {OUTPUT_REPORT}")
    print("Secrets printed: NÃO")
    print("LIVE: BLOQUEADO")

    return (
        0
        if result.get("preauthorization_ready")
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
