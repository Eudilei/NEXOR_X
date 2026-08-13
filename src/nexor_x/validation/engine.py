from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ValidationSnapshotInput:
    paper_trades: int
    profit_factor: float
    expected_r: float
    drawdown_pct: float
    recent_profit_factor: float
    recent_expected_r: float
    walk_forward_pass_ratio: float
    monte_carlo_ruin_probability: float
    brier_score_oos: float
    calibration_ece_oos: float
    integration_healthy: bool
    recovery_ok: bool
    supervisor_paper_allowed: bool
    supervisor_testnet_allowed: bool
    operational_incidents: int
    critical_test_failures: int


@dataclass(frozen=True, slots=True)
class ValidationSnapshotReport:
    status: str
    checks: dict[str, bool]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    paper_validation_ready: bool
    testnet_validation_ready: bool
    live_validation_ready: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["blockers"] = list(self.blockers)
        data["warnings"] = list(self.warnings)
        return data


class ValidationSnapshotEngine:
    """Aggregates the evidence needed before long-run validation.

    This is not the CQO certification itself. It is a pre-validation snapshot
    showing whether the system is ready to begin or continue PAPER/TESTNET runs.
    """

    def __init__(
        self,
        *,
        minimum_paper_trades: int = 200,
        minimum_profit_factor: float = 1.10,
        minimum_expected_r: float = 0.01,
        maximum_drawdown_pct: float = 20.0,
        minimum_recent_profit_factor: float = 1.00,
        minimum_recent_expected_r: float = 0.0,
        minimum_walk_forward_pass_ratio: float = 0.60,
        maximum_ruin_probability: float = 0.05,
        maximum_brier_score_oos: float = 0.30,
        maximum_ece_oos: float = 0.12,
    ) -> None:
        self.minimum_paper_trades = minimum_paper_trades
        self.minimum_profit_factor = minimum_profit_factor
        self.minimum_expected_r = minimum_expected_r
        self.maximum_drawdown_pct = maximum_drawdown_pct
        self.minimum_recent_profit_factor = minimum_recent_profit_factor
        self.minimum_recent_expected_r = minimum_recent_expected_r
        self.minimum_walk_forward_pass_ratio = minimum_walk_forward_pass_ratio
        self.maximum_ruin_probability = maximum_ruin_probability
        self.maximum_brier_score_oos = maximum_brier_score_oos
        self.maximum_ece_oos = maximum_ece_oos

    def evaluate(self, inputs: ValidationSnapshotInput) -> ValidationSnapshotReport:
        checks = {
            "MINIMUM_PAPER_TRADES": inputs.paper_trades >= self.minimum_paper_trades,
            "PROFIT_FACTOR": inputs.profit_factor >= self.minimum_profit_factor,
            "EXPECTED_R": inputs.expected_r >= self.minimum_expected_r,
            "DRAWDOWN": inputs.drawdown_pct <= self.maximum_drawdown_pct,
            "RECENT_PROFIT_FACTOR": (
                inputs.recent_profit_factor >= self.minimum_recent_profit_factor
            ),
            "RECENT_EXPECTED_R": (
                inputs.recent_expected_r >= self.minimum_recent_expected_r
            ),
            "WALK_FORWARD": (
                inputs.walk_forward_pass_ratio
                >= self.minimum_walk_forward_pass_ratio
            ),
            "MONTE_CARLO": (
                inputs.monte_carlo_ruin_probability
                <= self.maximum_ruin_probability
            ),
            "BRIER_OOS": inputs.brier_score_oos <= self.maximum_brier_score_oos,
            "ECE_OOS": inputs.calibration_ece_oos <= self.maximum_ece_oos,
            "INTEGRATION_HEALTH": inputs.integration_healthy,
            "RECOVERY": inputs.recovery_ok,
            "SUPERVISOR_PAPER": inputs.supervisor_paper_allowed,
            "SUPERVISOR_TESTNET": inputs.supervisor_testnet_allowed,
            "NO_OPERATIONAL_INCIDENTS": inputs.operational_incidents == 0,
            "NO_CRITICAL_TEST_FAILURES": inputs.critical_test_failures == 0,
        }

        paper_names = (
            "MINIMUM_PAPER_TRADES",
            "PROFIT_FACTOR",
            "EXPECTED_R",
            "DRAWDOWN",
            "RECENT_PROFIT_FACTOR",
            "RECENT_EXPECTED_R",
            "WALK_FORWARD",
            "MONTE_CARLO",
            "BRIER_OOS",
            "ECE_OOS",
            "INTEGRATION_HEALTH",
            "SUPERVISOR_PAPER",
            "NO_OPERATIONAL_INCIDENTS",
            "NO_CRITICAL_TEST_FAILURES",
        )
        testnet_names = paper_names + (
            "RECOVERY",
            "SUPERVISOR_TESTNET",
        )

        blockers = tuple(name for name, ok in checks.items() if not ok)
        paper_ready = all(checks[name] for name in paper_names)
        testnet_ready = all(checks[name] for name in testnet_names)

        warnings: list[str] = ["LIVE_REMAINS_BLOCKED"]
        if inputs.paper_trades < 1000:
            warnings.append("CQO_SAMPLE_NOT_YET_REACHED")

        if paper_ready and testnet_ready:
            status = "READY_FOR_LONG_RUN_VALIDATION"
        elif paper_ready:
            status = "PAPER_READY_TESTNET_BLOCKED"
        else:
            status = "NOT_READY_FOR_LONG_RUN_VALIDATION"

        return ValidationSnapshotReport(
            status=status,
            checks=checks,
            blockers=blockers,
            warnings=tuple(warnings),
            paper_validation_ready=paper_ready,
            testnet_validation_ready=testnet_ready,
            live_validation_ready=False,
        )
