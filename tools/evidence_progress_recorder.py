
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
import time
from typing import Any
from urllib import error, request


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_INTERVAL_SECONDS = 30 * 60


class EvidenceProgressRecorder:
    """Coletor read-only de progresso de validação/certificação."""

    ENDPOINTS = (
        "/api/live/certification",
        "/api/validation/final-snapshot",
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

    def collect(self) -> dict[str, Any]:
        certification = self._get("/api/live/certification")
        snapshot = self._get("/api/validation/final-snapshot")
        release_candidate = self._get(
            "/api/validation/release-candidate"
        )

        result = {
            "timestamp": datetime.now(UTC).isoformat(),
            "certification": certification,
            "snapshot": snapshot,
            "release_candidate": release_candidate,
            "summary": self._summary(
                certification=certification,
                snapshot=snapshot,
                release_candidate=release_candidate,
            ),
            "live_allowed": False,
        }

        self._persist(result)
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

    @staticmethod
    def _summary(
        *,
        certification: dict[str, Any],
        snapshot: dict[str, Any],
        release_candidate: dict[str, Any],
    ) -> dict[str, Any]:
        metrics = certification.get("metrics")
        if not isinstance(metrics, dict):
            metrics = {}

        blockers = list(
            certification.get("blockers") or []
        )
        blockers.extend(
            str(item)
            for item in snapshot.get("blockers") or []
        )
        blockers = list(dict.fromkeys(str(x) for x in blockers))

        return {
            "evidence_certified": bool(
                certification.get(
                    "evidence_certified",
                    False,
                )
            ),
            "candidate_ready": bool(
                snapshot.get("candidate_ready", False)
            ),
            "validation_status": snapshot.get(
                "validation_status",
                "UNKNOWN",
            ),
            "validation_progress_percent": float(
                snapshot.get(
                    "validation_progress_percent",
                    0.0,
                )
            ),
            "validation_passes": int(
                snapshot.get("validation_passes", 0)
            ),
            "validation_required_passes": int(
                snapshot.get(
                    "validation_required_passes",
                    20,
                )
            ),
            "release_candidate_status": (
                release_candidate.get(
                    "status",
                    "UNKNOWN",
                )
            ),
            "blockers": blockers,
            "metrics": metrics,
            "live_allowed": False,
        }

    def _persist(self, result: dict[str, Any]) -> None:
        self.report_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        history = (
            self.report_dir
            / "evidence_progress_history.jsonl"
        )
        with history.open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    result,
                    ensure_ascii=False,
                )
                + "\n"
            )

        latest = (
            self.report_dir
            / "evidence_progress_latest.json"
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


def print_summary(result: dict[str, Any]) -> None:
    summary = result.get("summary", {})

    print(
        "Evidence certified:",
        "SIM"
        if summary.get("evidence_certified")
        else "NÃO",
    )
    print(
        "Validation:",
        summary.get("validation_status", "UNKNOWN"),
        f"{summary.get('validation_progress_percent', 0)}%",
    )
    print(
        "Passes:",
        f"{summary.get('validation_passes', 0)}/"
        f"{summary.get('validation_required_passes', 0)}",
    )
    print(
        "Release Candidate:",
        summary.get(
            "release_candidate_status",
            "UNKNOWN",
        ),
    )

    metrics = summary.get("metrics") or {}
    if metrics:
        print(
            "Certification metrics:",
            json.dumps(
                metrics,
                ensure_ascii=False,
            ),
        )

    blockers = summary.get("blockers") or []
    if blockers:
        print(
            "Blockers:",
            " | ".join(str(x) for x in blockers),
        )

    print("LIVE: BLOQUEADO")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once",
        action="store_true",
        help="Executa uma coleta e encerra.",
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
            "NEXOR_EVIDENCE_INTERVAL_SECONDS",
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

    recorder = EvidenceProgressRecorder(
        base_url=base_url,
        admin_token=token,
    )

    while True:
        try:
            result = recorder.collect()
            print_summary(result)
        except Exception as exc:
            print(
                f"EVIDENCE_COLLECTION_ERROR: {exc}",
                file=sys.stderr,
            )
            if args.once:
                return 1

        if args.once:
            return 0

        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
