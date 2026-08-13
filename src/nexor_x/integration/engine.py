from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class IntegrationHealthInput:
    database_ok: bool
    market_ok: bool
    scanner_ok: bool
    strategy_ok: bool
    allocation_ok: bool
    recovery_ok: bool
    supervisor_ok: bool
    certification_ok: bool
    update_registry_ok: bool
    testnet_connector_ok: bool
    critical_test_failures: int = 0
    operational_incidents: int = 0


@dataclass(frozen=True, slots=True)
class IntegrationHealthReport:
    status: str
    healthy: bool
    checks: dict[str, bool]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    paper_ready: bool
    testnet_ready: bool
    live_ready: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["blockers"] = list(self.blockers)
        data["warnings"] = list(self.warnings)
        return data


class IntegrationHealthEngine:
    """Consolidates subsystem readiness into one end-to-end health verdict.

    This is an observability gate only. It does not enable trading modes.
    """

    def evaluate(self, inputs: IntegrationHealthInput) -> IntegrationHealthReport:
        checks = {
            "DATABASE": inputs.database_ok,
            "MARKET": inputs.market_ok,
            "SCANNER": inputs.scanner_ok,
            "STRATEGY": inputs.strategy_ok,
            "ALLOCATION": inputs.allocation_ok,
            "RECOVERY": inputs.recovery_ok,
            "SUPERVISOR": inputs.supervisor_ok,
            "CERTIFICATION": inputs.certification_ok,
            "UPDATE_REGISTRY": inputs.update_registry_ok,
            "TESTNET_CONNECTOR": inputs.testnet_connector_ok,
            "NO_CRITICAL_TEST_FAILURES": inputs.critical_test_failures == 0,
            "NO_OPERATIONAL_INCIDENTS": inputs.operational_incidents == 0,
        }

        core_names = (
            "DATABASE",
            "MARKET",
            "SCANNER",
            "STRATEGY",
            "ALLOCATION",
            "UPDATE_REGISTRY",
            "NO_CRITICAL_TEST_FAILURES",
            "NO_OPERATIONAL_INCIDENTS",
        )
        testnet_names = core_names + (
            "RECOVERY",
            "SUPERVISOR",
            "TESTNET_CONNECTOR",
        )

        blockers = tuple(name for name, ok in checks.items() if not ok)
        paper_ready = all(checks[name] for name in core_names)
        testnet_ready = all(checks[name] for name in testnet_names)

        warnings: list[str] = []
        if not checks["CERTIFICATION"]:
            warnings.append("CERTIFICATION_NOT_PASSED")
        warnings.append("LIVE_REMAINS_BLOCKED")

        if paper_ready and testnet_ready:
            status = "INTEGRATION_HEALTHY"
            healthy = True
        elif paper_ready:
            status = "PAPER_HEALTHY_TESTNET_BLOCKED"
            healthy = False
        else:
            status = "INTEGRATION_DEGRADED"
            healthy = False

        return IntegrationHealthReport(
            status=status,
            healthy=healthy,
            checks=checks,
            blockers=blockers,
            warnings=tuple(warnings),
            paper_ready=paper_ready,
            testnet_ready=testnet_ready,
            live_ready=False,
        )
