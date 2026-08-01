from __future__ import annotations

from datetime import UTC, datetime

from nexor_x.evidence.models import Evidence
from nexor_x.laboratory.models import CalibrationEstimate

from .models import EdgeDecision, QuantAssessment


class QuantBrain:
    """Aggregates evidence and optionally attaches causal laboratory calibration."""

    def assess(
        self,
        symbol: str,
        evidences: tuple[Evidence, ...],
        calibration: CalibrationEstimate | None = None,
    ) -> QuantAssessment:
        if not evidences:
            return self._empty(symbol, evidences)

        directional = [e for e in evidences if e.signed_value != 0.0]
        coverage = min(len(evidences) / 8.0, 1.0)
        raw_sum = sum(e.signed_value for e in directional)
        denominator = sum(abs(e.signed_value) for e in directional)
        normalized = raw_sum / denominator if denominator else 0.0
        confidence = round(min(abs(normalized) * coverage, 1.0), 4)
        raw_edge = round(normalized, 4)

        rationale: list[str] = [
            f"{len(directional)} evidencias direcionais de {len(evidences)} evidencias totais"
        ]
        if coverage < 0.35 or denominator == 0.0:
            decision = EdgeDecision.INSUFFICIENT_DATA
            rationale.append("cobertura direcional insuficiente")
        elif raw_edge >= 0.30 and confidence >= 0.12:
            decision = EdgeDecision.LONG_BIAS
            rationale.append("conjunto de evidencias inclina para alta")
        elif raw_edge <= -0.30 and confidence >= 0.12:
            decision = EdgeDecision.SHORT_BIAS
            rationale.append("conjunto de evidencias inclina para baixa")
        else:
            decision = EdgeDecision.NO_EDGE
            rationale.append("evidencias conflitantes ou fracas")

        ready = bool(calibration and calibration.ready)
        if ready:
            assert calibration is not None
            rationale.append(
                f"calibracao historica com {calibration.sample_count} observacoes concluidas"
            )
        else:
            rationale.append(
                calibration.reason if calibration else "avaliacao ainda nao calibrada"
            )

        # Sprint 6 never authorizes execution. Certification is a separate gate.
        return QuantAssessment(
            symbol=symbol,
            decision=decision,
            raw_edge=raw_edge,
            evidence_coverage=round(coverage, 4),
            confidence=confidence,
            calibrated=ready,
            win_probability=calibration.win_probability if ready and calibration else None,
            expected_r=calibration.expected_r if ready and calibration else None,
            profit_factor=calibration.profit_factor if ready and calibration else None,
            calibration_samples=calibration.sample_count if calibration else 0,
            execution_allowed=False,
            rationale=tuple(rationale),
            evidences=evidences,
            evaluated_at=datetime.now(UTC),
        )

    @staticmethod
    def _empty(symbol: str, evidences: tuple[Evidence, ...]) -> QuantAssessment:
        return QuantAssessment(
            symbol=symbol,
            decision=EdgeDecision.INSUFFICIENT_DATA,
            raw_edge=0.0,
            evidence_coverage=0.0,
            confidence=0.0,
            calibrated=False,
            win_probability=None,
            expected_r=None,
            profit_factor=None,
            calibration_samples=0,
            execution_allowed=False,
            rationale=("nenhuma evidencia disponivel",),
            evidences=evidences,
            evaluated_at=datetime.now(UTC),
        )
