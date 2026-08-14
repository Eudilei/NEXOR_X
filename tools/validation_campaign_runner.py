
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import time
from typing import Any
from urllib import error, request


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_INTERVAL_SECONDS = 30 * 60


class ValidationCampaignRunner:
    """Cliente operacional; não executa ordens de trading."""

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

    def cycle(self) -> dict[str, Any]:
        tick = self._call(
            "/api/validation/final-campaign/tick",
            method="POST",
        )
        snapshot = self._call(
            "/api/validation/final-snapshot",
            method="GET",
        )
        release_candidate = self._call(
            "/api/validation/release-candidate",
            method="GET",
        )

        result = {
            "timestamp": datetime.now(UTC).isoformat(),
            "tick": tick,
            "snapshot": snapshot,
            "release_candidate": release_candidate,
            "live_allowed": False,
        }
        self._persist(result)
        return result

    def _call(
        self,
        path: str,
        *,
        method: str,
    ) -> dict[str, Any]:
        req = request.Request(
            self.base_url + path,
            method=method,
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
                f"{method} {path} -> HTTP {exc.code}: {body}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(
                f"{method} {path} -> conexão falhou: {exc.reason}"
            ) from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"{method} {path} retornou JSON inválido"
            ) from exc

        if not isinstance(payload, dict):
            raise RuntimeError(
                f"{method} {path} retornou formato inesperado"
            )
        return payload

    def _persist(self, result: dict[str, Any]) -> None:
        self.report_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        history = (
            self.report_dir
            / "validation_campaign_history.jsonl"
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
            / "validation_campaign_latest.json"
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
    tick = result.get("tick", {})
    snapshot = result.get("snapshot", {})
    rc = result.get("release_candidate", {})

    print(
        "Validation:",
        snapshot.get("validation_status", "UNKNOWN"),
        f"{snapshot.get('validation_progress_percent', 0)}%",
    )
    print(
        "Passes:",
        f"{snapshot.get('validation_passes', 0)}/"
        f"{snapshot.get('validation_required_passes', 0)}",
    )
    print(
        "Sample:",
        tick.get("sample_reason", "UNKNOWN"),
    )
    print(
        "Final status:",
        snapshot.get("status", "UNKNOWN"),
    )
    print(
        "Release Candidate:",
        rc.get("status", "UNKNOWN"),
    )
    print("LIVE: BLOQUEADO")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once",
        action="store_true",
        help="Executa um único ciclo e encerra.",
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
            "NEXOR_VALIDATION_INTERVAL_SECONDS",
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
            "ERRO: intervalo mínimo permitido pelo runner é 1800 segundos.",
            file=sys.stderr,
        )
        return 2

    runner = ValidationCampaignRunner(
        base_url=base_url,
        admin_token=token,
    )

    while True:
        try:
            result = runner.cycle()
            print_summary(result)
        except Exception as exc:
            print(
                f"VALIDATION_CYCLE_ERROR: {exc}",
                file=sys.stderr,
            )
            if args.once:
                return 1

        if args.once:
            return 0

        time.sleep(interval)


if __name__ == "__main__":
    import sys
    raise SystemExit(main())
