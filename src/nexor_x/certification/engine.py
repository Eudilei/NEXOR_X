from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .models import CertificationEvidence, CertificationResult


@dataclass(frozen=True, slots=True)
class CertificationPolicy:
    minimum_paper_trades: int = 1000
    minimum_profit_factor: float = 1.40
    minimum_expected_r: float = 0.05
    maximum_drawdown_pct: float = 15.0
    minimum_walk_forward_pass_ratio: float = 0.70
    maximum_monte_carlo_ruin_probability: float = 0.02
    maximum_brier_score_oos: float = 0.24
    maximum_calibration_ece_oos: float = 0.08
    maximum_operational_incidents: int = 0
    maximum_critical_test_failures: int = 0
    minimum_days_in_paper: int = 30
    minimum_recent_profit_factor: float = 1.15
    minimum_recent_expected_r: float = 0.01

    def __post_init__(self) -> None:
        if self.minimum_paper_trades < 1:
            raise ValueError("minimum_paper_trades must be positive")
        if self.minimum_days_in_paper < 1:
            raise ValueError("minimum_days_in_paper must be positive")
        for value, name in (
            (self.maximum_drawdown_pct, "maximum_drawdown_pct"),
            (self.maximum_monte_carlo_ruin_probability, "maximum_monte_carlo_ruin_probability"),
            (self.maximum_brier_score_oos, "maximum_brier_score_oos"),
            (self.maximum_calibration_ece_oos, "maximum_calibration_ece_oos"),
        ):
            if value < 0:
                raise ValueError(f"{name} cannot be negative")


class CQOCertificationEngine:
    """Issues a certification verdict without changing runtime mode.

    A PASS means the statistical and operational evidence met the configured
    policy. LIVE remains blocked until a separate manual approval is recorded.
    """

    def __init__(self, policy: CertificationPolicy | None = None) -> None:
        self.policy = policy or CertificationPolicy()

    def evaluate(self, evidence: CertificationEvidence) -> CertificationResult:
        p = self.policy
        finite_values = (
            evidence.profit_factor,
            evidence.expected_r,
            evidence.maximum_drawdown_pct,
            evidence.walk_forward_pass_ratio,
            evidence.monte_carlo_ruin_probability,
            evidence.brier_score_oos,
            evidence.calibration_ece_oos,
            evidence.recent_profit_factor,
            evidence.recent_expected_r,
        )
        finite_metrics = all(isfinite(value) for value in finite_values)

        checks = {
            "FINITE_METRICS": finite_metrics,
            "MINIMUM_PAPER_TRADES": evidence.paper_trades >= p.minimum_paper_trades,
            "MINIMUM_PROFIT_FACTOR": evidence.profit_factor >= p.minimum_profit_factor,
            "POSITIVE_EXPECTED_R": evidence.expected_r >= p.minimum_expected_r,
            "MAXIMUM_DRAWDOWN": evidence.maximum_drawdown_pct <= p.maximum_drawdown_pct,
            "WALK_FORWARD": (
                evidence.walk_forward_pass_ratio >= p.minimum_walk_forward_pass_ratio
            ),
            "MONTE_CARLO": (
                evidence.monte_carlo_ruin_probability
                <= p.maximum_monte_carlo_ruin_probability
            ),
            "BRIER_OOS": evidence.brier_score_oos <= p.maximum_brier_score_oos,
            "ECE_OOS": evidence.calibration_ece_oos <= p.maximum_calibration_ece_oos,
            "NO_OPERATIONAL_INCIDENTS": (
                evidence.operational_incidents <= p.maximum_operational_incidents
            ),
            "NO_CRITICAL_TEST_FAILURES": (
                evidence.critical_test_failures <= p.maximum_critical_test_failures
            ),
            "MINIMUM_PAPER_DAYS": evidence.days_in_paper >= p.minimum_days_in_paper,
            "RECENT_PROFIT_FACTOR": (
                evidence.recent_profit_factor >= p.minimum_recent_profit_factor
            ),
            "RECENT_EXPECTED_R": (
                evidence.recent_expected_r >= p.minimum_recent_expected_r
            ),
            "DATA_FRESHNESS": evidence.data_freshness_ok,
            "RECONCILIATION": evidence.reconciliation_ok,
            "SECRETS_CONFIGURED": evidence.secrets_configured,
            "LIVE_CONNECTOR_TESTED": evidence.live_connector_tested,
        }

        blockers = tuple(name for name, passed in checks.items() if not passed)
        warnings: list[str] = []
        if not evidence.manual_owner_approval:
            warnings.append("MANUAL_OWNER_APPROVAL_PENDING")

        statistical_and_operational_pass = not blockers

        if statistical_and_operational_pass and evidence.manual_owner_approval:
            status = "CERTIFIED_PENDING_MODE_SWITCH"
            passed = True
        elif statistical_and_operational_pass:
            status = "TECHNICALLY_APPROVED_MANUAL_APPROVAL_REQUIRED"
            passed = True
        else:
            status = "REJECTED"
            passed = False

        return CertificationResult(
            status=status,
            passed=passed,
            checks=checks,
            blockers=blockers,
            warnings=tuple(warnings),
            evidence=evidence,
            live_execution_allowed=False,
            paper_execution_allowed=True,
            requires_manual_approval=not evidence.manual_owner_approval,
        )
