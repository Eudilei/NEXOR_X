from __future__ import annotations

from datetime import UTC, datetime

from nexor_x.evidence.models import Evidence

from .models import EdgeDecision, QuantAssessment


class QuantBrain:
    """Aggregates evidence into an explainable, non-calibrated edge assessment.

    This first implementation deliberately cannot authorize execution. Its
    confidence is an evidence-consistency measure, not a probability of profit.
    Historical calibration and expected-value estimation are future laboratory
    responsibilities.
    """

    def assess(self, symbol: str, evidences: tuple[Evidence, ...]) -> QuantAssessment:
        if not evidences:
            return QuantAssessment(
                symbol=symbol,
                decision=EdgeDecision.INSUFFICIENT_DATA,
                raw_edge=0.0,
                evidence_coverage=0.0,
                confidence=0.0,
                calibrated=False,
                execution_allowed=False,
                rationale=("nenhuma evidencia disponivel",),
                evidences=evidences,
                evaluated_at=datetime.now(UTC),
            )

        directional = [e for e in evidences if e.signed_value != 0.0]
        coverage = min(len(evidences) / 8.0, 1.0)
        raw_edge = sum(e.signed_value for e in directional)
        denominator = sum(abs(e.signed_value) for e in directional)
        normalized = raw_edge / denominator if denominator else 0.0
        agreement = abs(normalized)
        confidence = round(min(agreement * coverage, 1.0), 4)
        raw_edge = round(normalized, 4)

        rationale: list[str] = [
            f"{len(directional)} evidencias direcionais de {len(evidences)} evidencias totais",
            "avaliacao ainda nao calibrada por resultados historicos",
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

        return QuantAssessment(
            symbol=symbol,
            decision=decision,
            raw_edge=raw_edge,
            evidence_coverage=round(coverage, 4),
            confidence=confidence,
            calibrated=False,
            execution_allowed=False,
            rationale=tuple(rationale),
            evidences=evidences,
            evaluated_at=datetime.now(UTC),
        )
