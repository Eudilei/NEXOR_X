from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class CertificationEvidence:
    paper_trades: int
    profit_factor: float
    expected_r: float
    maximum_drawdown_pct: float
    walk_forward_pass_ratio: float
    monte_carlo_ruin_probability: float
    brier_score_oos: float
    calibration_ece_oos: float
    operational_incidents: int
    critical_test_failures: int
    days_in_paper: int
    recent_profit_factor: float
    recent_expected_r: float
    data_freshness_ok: bool
    reconciliation_ok: bool
    secrets_configured: bool
    live_connector_tested: bool
    manual_owner_approval: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CertificationResult:
    status: str
    passed: bool
    checks: dict[str, bool]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    evidence: CertificationEvidence
    live_execution_allowed: bool = False
    paper_execution_allowed: bool = True
    requires_manual_approval: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "passed": self.passed,
            "checks": dict(self.checks),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "evidence": self.evidence.to_dict(),
            "live_execution_allowed": self.live_execution_allowed,
            "paper_execution_allowed": self.paper_execution_allowed,
            "requires_manual_approval": self.requires_manual_approval,
            "created_at": self.created_at.isoformat(),
        }
