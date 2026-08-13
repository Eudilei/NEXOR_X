from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ValidationCampaignInput:
    days_running: int
    paper_trades: int
    profit_factor: float
    expected_r: float
    drawdown_pct: float
    recent_profit_factor: float
    recent_expected_r: float
    operational_incidents: int
    critical_test_failures: int
    integration_healthy: bool
    recovery_ok: bool
    supervisor_paper_allowed: bool
    supervisor_testnet_allowed: bool


@dataclass(frozen=True, slots=True)
class ValidationCampaignReport:
    phase: str
    continue_campaign: bool
    paper_allowed: bool
    testnet_allowed: bool
    live_allowed: bool
    milestones: dict[str, bool]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["blockers"] = list(self.blockers)
        data["warnings"] = list(self.warnings)
        return data


class ValidationCampaignEngine:
    """Controls long-run PAPER/TESTNET validation milestones.

    It never enables LIVE. Its role is to decide whether validation should
    continue, be paused, or has reached the minimum evidence milestone.
    """

    def __init__(
        self,
        *,
        minimum_days: int = 30,
        minimum_paper_trades: int = 1000,
        minimum_profit_factor: float = 1.40,
        minimum_expected_r: float = 0.05,
        maximum_drawdown_pct: float = 15.0,
        minimum_recent_profit_factor: float = 1.15,
        minimum_recent_expected_r: float = 0.01,
    ) -> None:
        self.minimum_days = minimum_days
        self.minimum_paper_trades = minimum_paper_trades
        self.minimum_profit_factor = minimum_profit_factor
        self.minimum_expected_r = minimum_expected_r
        self.maximum_drawdown_pct = maximum_drawdown_pct
        self.minimum_recent_profit_factor = minimum_recent_profit_factor
        self.minimum_recent_expected_r = minimum_recent_expected_r

    def evaluate(
        self,
        inputs: ValidationCampaignInput,
    ) -> ValidationCampaignReport:
        milestones = {
            "MINIMUM_DAYS": inputs.days_running >= self.minimum_days,
            "MINIMUM_PAPER_TRADES": (
                inputs.paper_trades >= self.minimum_paper_trades
            ),
            "PROFIT_FACTOR": (
                inputs.profit_factor >= self.minimum_profit_factor
            ),
            "EXPECTED_R": inputs.expected_r >= self.minimum_expected_r,
            "DRAWDOWN": inputs.drawdown_pct <= self.maximum_drawdown_pct,
            "RECENT_PROFIT_FACTOR": (
                inputs.recent_profit_factor
                >= self.minimum_recent_profit_factor
            ),
            "RECENT_EXPECTED_R": (
                inputs.recent_expected_r >= self.minimum_recent_expected_r
            ),
            "INTEGRATION_HEALTH": inputs.integration_healthy,
            "RECOVERY": inputs.recovery_ok,
            "SUPERVISOR_PAPER": inputs.supervisor_paper_allowed,
            "SUPERVISOR_TESTNET": inputs.supervisor_testnet_allowed,
            "NO_OPERATIONAL_INCIDENTS": inputs.operational_incidents == 0,
            "NO_CRITICAL_TEST_FAILURES": inputs.critical_test_failures == 0,
        }

        hard_blockers = tuple(
            name
            for name in (
                "DRAWDOWN",
                "INTEGRATION_HEALTH",
                "RECOVERY",
                "SUPERVISOR_PAPER",
                "NO_OPERATIONAL_INCIDENTS",
                "NO_CRITICAL_TEST_FAILURES",
            )
            if not milestones[name]
        )

        paper_allowed = (
            milestones["SUPERVISOR_PAPER"]
            and milestones["INTEGRATION_HEALTH"]
            and milestones["NO_OPERATIONAL_INCIDENTS"]
            and milestones["NO_CRITICAL_TEST_FAILURES"]
            and milestones["DRAWDOWN"]
        )
        testnet_allowed = (
            paper_allowed
            and milestones["RECOVERY"]
            and milestones["SUPERVISOR_TESTNET"]
        )

        evidence_complete = all(milestones.values())
        warnings: list[str] = ["LIVE_REMAINS_BLOCKED"]

        if hard_blockers:
            phase = "PAUSED_BY_RISK"
            continue_campaign = False
        elif evidence_complete:
            phase = "EVIDENCE_MILESTONE_REACHED"
            continue_campaign = False
            warnings.append("CQO_REVIEW_REQUIRED")
        else:
            phase = "VALIDATION_IN_PROGRESS"
            continue_campaign = True

        return ValidationCampaignReport(
            phase=phase,
            continue_campaign=continue_campaign,
            paper_allowed=paper_allowed,
            testnet_allowed=testnet_allowed,
            live_allowed=False,
            milestones=milestones,
            blockers=hard_blockers,
            warnings=tuple(warnings),
        )
