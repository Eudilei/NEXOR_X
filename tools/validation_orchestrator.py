
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


MIN_INTERVAL_SECONDS = 30 * 60
LOCK_PATH = Path("data/validation_orchestrator.lock")
HEARTBEAT_PATH = Path(
    "reports/validation_orchestrator_heartbeat.json"
)
HISTORY_PATH = Path(
    "reports/validation_orchestrator_history.jsonl"
)


class InstanceLock:
    def __init__(
        self,
        path: Path = LOCK_PATH,
    ) -> None:
        self.path = path
        self.acquired = False

    def acquire(self) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if self.path.exists():
            try:
                payload = json.loads(
                    self.path.read_text(encoding="utf-8")
                )
            except Exception:
                payload = {}

            pid = payload.get("pid")
            if isinstance(pid, int) and _pid_exists(pid):
                raise RuntimeError(
                    f"Orquestrador já está ativo no PID {pid}"
                )

            self.path.unlink(missing_ok=True)

        payload = {
            "pid": os.getpid(),
            "started_at": datetime.now(UTC).isoformat(),
        }
        self.path.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )
        self.acquired = True

    def release(self) -> None:
        if self.acquired:
            self.path.unlink(missing_ok=True)
            self.acquired = False

    def __enter__(self) -> "InstanceLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.release()
        return False


def _pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class ValidationOrchestrator:
    def __init__(
        self,
        *,
        repo: Path | None = None,
        python_executable: str | None = None,
    ) -> None:
        self.repo = Path.cwd() if repo is None else Path(repo)
        self.python = python_executable or sys.executable

    def run_cycle(self) -> dict[str, Any]:
        started = datetime.now(UTC)

        steps: list[dict[str, Any]] = []

        steps.append(
            self._run_tool(
                "rc_verify",
                "tools/rc_verify.py",
                acceptable_codes={0},
            )
        )

        steps.append(
            self._run_tool(
                "validation_campaign",
                "tools/validation_campaign_runner.py",
                args=["--once"],
                acceptable_codes={0},
            )
        )

        steps.append(
            self._run_tool(
                "evidence_progress",
                "tools/evidence_progress_recorder.py",
                args=["--once"],
                acceptable_codes={0},
            )
        )

        steps.append(
            self._run_tool(
                "evidence_watchdog",
                "tools/evidence_completion_watchdog.py",
                args=["--once"],
                acceptable_codes={0},
            )
        )

        bundle = self.repo / "reports/final_evidence_bundle.json"
        integrity_report = (
            self.repo
            / "reports/final_evidence_integrity_audit.json"
        )

        if bundle.exists():
            steps.append(
                self._run_tool(
                    "evidence_integrity",
                    "tools/final_evidence_integrity_audit.py",
                    acceptable_codes={0, 1},
                )
            )
        else:
            steps.append(
                {
                    "name": "evidence_integrity",
                    "status": "SKIPPED",
                    "reason": "FINAL_EVIDENCE_BUNDLE_NOT_READY",
                }
            )

        evidence_verified = False
        if integrity_report.exists():
            try:
                payload = json.loads(
                    integrity_report.read_text(
                        encoding="utf-8"
                    )
                )
            except Exception:
                payload = {}
            evidence_verified = (
                payload.get("status")
                == "FINAL_EVIDENCE_VERIFIED"
                and payload.get("verified") is True
            )

        if evidence_verified:
            steps.append(
                self._run_tool(
                    "live_preauthorization",
                    "tools/live_preauthorization_dossier.py",
                    acceptable_codes={0, 1},
                )
            )
        else:
            steps.append(
                {
                    "name": "live_preauthorization",
                    "status": "SKIPPED",
                    "reason": "FINAL_EVIDENCE_NOT_VERIFIED",
                }
            )

        hard_failures = [
            step["name"]
            for step in steps
            if step.get("status") == "FAILED"
            and step["name"] in {
                "rc_verify",
                "validation_campaign",
                "evidence_progress",
                "evidence_watchdog",
            }
        ]

        completed = datetime.now(UTC)

        report = {
            "status": (
                "ORCHESTRATOR_OK"
                if not hard_failures
                else "ORCHESTRATOR_DEGRADED"
            ),
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": round(
                (completed - started).total_seconds(),
                3,
            ),
            "steps": steps,
            "hard_failures": hard_failures,
            "final_evidence_verified": evidence_verified,
            "live_allowed": False,
            "live_certified": False,
            "trading_runtime_changed": False,
        }

        self._persist(report)
        return report

    def _run_tool(
        self,
        name: str,
        relative_path: str,
        *,
        args: list[str] | None = None,
        acceptable_codes: set[int],
    ) -> dict[str, Any]:
        path = self.repo / relative_path
        if not path.exists():
            return {
                "name": name,
                "status": "FAILED",
                "returncode": None,
                "reason": f"MISSING_TOOL:{relative_path}",
            }

        command = [
            self.python,
            str(path),
            *(args or []),
        ]

        completed = subprocess.run(
            command,
            cwd=self.repo,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )

        return {
            "name": name,
            "status": (
                "OK"
                if completed.returncode in acceptable_codes
                else "FAILED"
            ),
            "returncode": completed.returncode,
            "stdout_tail": completed.stdout[-2000:],
            "stderr_tail": completed.stderr[-2000:],
        }

    def _persist(
        self,
        report: dict[str, Any],
    ) -> None:
        HEARTBEAT_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp = HEARTBEAT_PATH.with_suffix(
            HEARTBEAT_PATH.suffix + ".tmp"
        )
        temp.write_text(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        temp.replace(HEARTBEAT_PATH)

        with HISTORY_PATH.open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    report,
                    ensure_ascii=False,
                )
                + "\n"
            )


def print_summary(
    report: dict[str, Any],
) -> None:
    print(report["status"])

    for step in report["steps"]:
        print(
            f"{step['name']}: {step['status']}"
        )

    print(
        "Final evidence:",
        (
            "VERIFIED"
            if report["final_evidence_verified"]
            else "PENDING"
        ),
    )
    print("LIVE: BLOQUEADO")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once",
        action="store_true",
        help="Executa um ciclo e encerra.",
    )
    args = parser.parse_args()

    interval = int(
        os.getenv(
            "NEXOR_VALIDATION_INTERVAL_SECONDS",
            str(MIN_INTERVAL_SECONDS),
        )
    )

    if interval < MIN_INTERVAL_SECONDS:
        print(
            "ERRO: intervalo mínimo é 1800 segundos.",
            file=sys.stderr,
        )
        return 2

    token = os.getenv(
        "NEXOR_ADMIN_TOKEN",
        "",
    ).strip()

    if not token:
        print(
            "ERRO: NEXOR_ADMIN_TOKEN não configurado.",
            file=sys.stderr,
        )
        return 2

    orchestrator = ValidationOrchestrator()

    try:
        with InstanceLock():
            while True:
                report = orchestrator.run_cycle()
                print_summary(report)

                if args.once:
                    return (
                        0
                        if report["status"] == "ORCHESTRATOR_OK"
                        else 1
                    )

                time.sleep(interval)
    except RuntimeError as exc:
        print(
            f"ERRO: {exc}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
