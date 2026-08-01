from nexor_x.evidence import Evidence, EvidenceDirection
from nexor_x.quant import EdgeDecision, QuantBrain


def ev(name: str, direction: EvidenceDirection, strength: float = 1.0) -> Evidence:
    return Evidence(name, direction, strength, 0.9, "test", ("x",))


def test_quant_brain_never_allows_execution_before_calibration() -> None:
    items = tuple(ev(str(i), EvidenceDirection.BULLISH) for i in range(4))
    assessment = QuantBrain().assess("BTCUSDT", items)
    assert assessment.decision is EdgeDecision.LONG_BIAS
    assert assessment.calibrated is False
    assert assessment.execution_allowed is False


def test_quant_brain_detects_conflict_as_no_edge() -> None:
    items = (
        ev("a", EvidenceDirection.BULLISH),
        ev("b", EvidenceDirection.BEARISH),
        ev("c", EvidenceDirection.BULLISH),
        ev("d", EvidenceDirection.BEARISH),
    )
    assessment = QuantBrain().assess("BTCUSDT", items)
    assert assessment.decision is EdgeDecision.NO_EDGE


def test_quant_brain_handles_empty_input() -> None:
    assessment = QuantBrain().assess("BTCUSDT", ())
    assert assessment.decision is EdgeDecision.INSUFFICIENT_DATA
