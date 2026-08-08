from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SupervisorInputs:
    mode: str
    recovery_ok: bool
    exchange_ready: bool
    certification_passed: bool
    live_connector_tested: bool
    data_freshness_ok: bool
    hard_stop_active: bool
    critical_test_failures: int
    operational_incidents: int

    def normalized_mode(self) -> str:
        return self.mode.strip().upper()


@dataclass(frozen=True, slots=True)
class SupervisorDecision:
    status: str
    paper_allowed: bool
    testnet_allowed: bool
    live_allowed: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["blockers"] = list(self.blockers)
        data["warnings"] = list(self.warnings)
        return data


class OperationalSupervisor:
    """Central operational gate.

    This engine is intentionally stricter than individual subsystem gates.
    LIVE remains impossible in Update 26 even when every technical criterion
    passes. It only decides whether PAPER or manual TESTNET actions are allowed.
    """

    def evaluate(self, inputs: SupervisorInputs) -> SupervisorDecision:
        mode = inputs.normalized_mode()
        blockers: list[str] = []
        warnings: list[str] = []

        if inputs.hard_stop_active:
            blockers.append("HARD_STOP_ACTIVE")
        if inputs.critical_test_failures > 0:
            blockers.append("CRITICAL_TEST_FAILURES")
        if inputs.operational_incidents > 0:
            blockers.append("OPERATIONAL_INCIDENTS")
        if not inputs.data_freshness_ok:
            blockers.append("STALE_MARKET_DATA")

        paper_allowed = not blockers

        testnet_blockers = list(blockers)
        if not inputs.recovery_ok:
            testnet_blockers.append("RECOVERY_NOT_CLEAN")
        if not inputs.exchange_ready:
            testnet_blockers.append("EXCHANGE_NOT_READY")
        if not inputs.live_connector_tested:
            testnet_blockers.append("CONNECTOR_NOT_TESTED")

        testnet_allowed = not testnet_blockers

        if mode == "LIVE":
            warnings.append("LIVE_MODE_REQUEST_IGNORED")
        if inputs.certification_passed:
            warnings.append("CERTIFICATION_DOES_NOT_ENABLE_LIVE")

        all_blockers = tuple(dict.fromkeys(testnet_blockers))
        if paper_allowed and testnet_allowed:
            status = "PAPER_AND_TESTNET_READY"
        elif paper_allowed:
            status = "PAPER_ONLY"
        else:
            status = "LOCKED"

        return SupervisorDecision(
            status=status,
            paper_allowed=paper_allowed,
            testnet_allowed=testnet_allowed,
            live_allowed=False,
            blockers=all_blockers,
            warnings=tuple(warnings),
        )
