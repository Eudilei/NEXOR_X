
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from typing import Any
from urllib import error, request


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_INTERVAL_SECONDS = 30 * 60


class EvidenceCompletionWatchdog:
    ENDPOINTS = (
        "/api/live/certification",
        "/api/validation/final-campaign",
        "/api/validation/final-completion",
        "/api/validation/release-candidate",
    )

    def __init__(
        self,
        *,
        base_url: str,
        admin_token: str,
        report_dir: str | Path = "reports",
        timeout_seconds: float = 15.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.admin_token = admin_token
        self.report_dir = Path(report_dir)
        self.timeout_seconds = timeout_seconds

    def evaluate(self) -> dict[str, Any]:
        certification = self._get("/api/live/certification")
        campaign = self._get("/api/validation/final-campaign")
        completion = self._get("/api/validation/final-completion")
        rc = self._get("/api/validation/release-candidate")

        requirements = {
            "release_candidate_ready": (
                rc.get("status") == "RC_READY"
                and rc.get("rc_ready") is True
            ),
            "technical_completion": (
                completion.get("status") == "TECHNICALLY_COMPLETE"
                and completion.get("technically_complete") is True
            ),
            "validation_campaign_complete": (
                campaign.get("status") == "COMPLETE"
                and campaign.get("completed") is True
            ),
            "candidate_ready": bool(
                certification.get("candidate_ready", False)
                or completion.get("candidate_ready", False)
            ),
            "evidence_certified": bool(
                certification.get("evidence_certified", False)
                and completion.get("evidence_certified", False)
            ),
            "live_still_blocked": (
                certification.get("live_allowed") is False
                and campaign.get("live_allowed") is False
                and completion.get("live_allowed") is False
                and rc.get("live_allowed") is False
            ),
        }

        pending = [
            name
            for name, passed in requirements.items()
            if not passed
        ]

        ready = not pending

        result = {
            "status": (
                "FINAL_EVIDENCE_READY"
                if ready
                else "EVIDENCE_PENDING"
            ),
            "final_evidence_ready": ready,
            "requirements": requirements,
            "pending_requirements": pending,
            "certification": certification,
            "campaign": campaign,
            "completion": completion,
            "release_candidate": rc,
            "live_allowed": False,
            "live_certified": False,
            "read_only": True,
            "evaluated_at": datetime.now(UTC).isoformat(),
        }

        self._persist_latest(result)

        if ready:
            bundle = self._build_bundle(result)
            self._persist_bundle(bundle)

        return result

    def _get(self, path: str) -> dict[str, Any]:
        req = request.Request(
            self.base_url + path,
            method="GET",
            headers={
                "X-NEXOR-ADMIN-TOKEN": self.admin_token,
                "Accept": "application/json",
            },
        )

        try:
            with request.urlopen(
                req,
                timeout=self.timeout_seconds,
            ) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            body = exc.read().decode(
                "utf-8",
                errors="replace",
            )
            raise RuntimeError(
                f"GET {path} -> HTTP {exc.code}: {body}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(
                f"GET {path} -> conexão falhou: {exc.reason}"
            ) from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"GET {path} retornou JSON inválido"
            ) from exc

        if not isinstance(payload, dict):
            raise RuntimeError(
                f"GET {path} retornou formato inesperado"
            )

        return payload

    def _build_bundle(
        self,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "bundle_type": "NEXOR_X_FINAL_EVIDENCE",
            "bundle_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "status": "FINAL_EVIDENCE_READY",
            "requirements": result["requirements"],
            "certification": result["certification"],
            "campaign": result["campaign"],
            "completion": result["completion"],
            "release_candidate": result["release_candidate"],
            "live_allowed": False,
            "live_certified": False,
        }

        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

        payload["sha256"] = hashlib.sha256(
            canonical
        ).hexdigest()

        return payload

    def _persist_latest(
        self,
        result: dict[str, Any],
    ) -> None:
        self.report_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        latest = (
            self.report_dir
            / "evidence_completion_latest.json"
        )
        tmp = latest.with_suffix(
            latest.suffix + ".tmp"
        )
        tmp.write_text(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        tmp.replace(latest)

    def _persist_bundle(
        self,
        bundle: dict[str, Any],
    ) -> None:
        self.report_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        bundle_path = (
            self.report_dir
            / "final_evidence_bundle.json"
        )
        bundle_path.write_text(
            json.dumps(
                bundle,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        digest_path = (
            self.report_dir
            / "final_evidence_bundle.sha256"
        )
        digest_path.write_text(
            f"{bundle['sha256']}  final_evidence_bundle.json\n",
            encoding="utf-8",
        )


def print_summary(result: dict[str, Any]) -> None:
    print(result["status"])

    pending = result.get("pending_requirements") or []
    if pending:
        print(
            "Pendências:",
            " | ".join(str(x) for x in pending),
        )

    if result.get("final_evidence_ready"):
        print(
            "Bundle:",
            "reports/final_evidence_bundle.json",
        )
        print(
            "SHA-256:",
            "reports/final_evidence_bundle.sha256",
        )

    print("LIVE: BLOQUEADO")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once",
        action="store_true",
        help="Executa uma verificação e encerra.",
    )
    args = parser.parse_args()

    base_url = os.getenv(
        "NEXOR_BASE_URL",
        DEFAULT_BASE_URL,
    )
    token = os.getenv(
        "NEXOR_ADMIN_TOKEN",
        "",
    ).strip()
    interval = int(
        os.getenv(
            "NEXOR_EVIDENCE_WATCH_INTERVAL_SECONDS",
            str(DEFAULT_INTERVAL_SECONDS),
        )
    )

    if not token:
        print(
            "ERRO: defina NEXOR_ADMIN_TOKEN antes de executar.",
            file=sys.stderr,
        )
        return 2

    if interval < DEFAULT_INTERVAL_SECONDS:
        print(
            "ERRO: intervalo mínimo permitido é 1800 segundos.",
            file=sys.stderr,
        )
        return 2

    watchdog = EvidenceCompletionWatchdog(
        base_url=base_url,
        admin_token=token,
    )

    while True:
        try:
            result = watchdog.evaluate()
            print_summary(result)
        except Exception as exc:
            print(
                f"EVIDENCE_WATCH_ERROR: {exc}",
                file=sys.stderr,
            )
            if args.once:
                return 1

        if args.once:
            return 0

        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
