from __future__ import annotations

from collections.abc import Iterable

from .models import CalibrationEstimate, OutcomeObservation


class CalibrationEngine:
    """Causal, bin-based calibration for raw edge values.

    It intentionally uses only completed observations supplied by the laboratory.
    No estimate is considered ready before the configured minimum sample size.
    """

    def __init__(self, minimum_samples: int = 30, bin_width: float = 0.20) -> None:
        if minimum_samples < 5:
            raise ValueError("minimum_samples must be at least 5")
        if not 0.05 <= bin_width <= 1.0:
            raise ValueError("bin_width must be between 0.05 and 1.0")
        self.minimum_samples = minimum_samples
        self.bin_width = bin_width

    def estimate(
        self,
        raw_edge: float,
        observations: Iterable[OutcomeObservation],
        *,
        decision: str | None = None,
        regime: str | None = None,
    ) -> CalibrationEstimate:
        center = max(-1.0, min(1.0, raw_edge))
        half = self.bin_width / 2.0
        lower = max(-1.0, center - half)
        upper = min(1.0, center + half)
        selected = [
            item
            for item in observations
            if lower <= item.raw_edge <= upper
            and (decision is None or item.decision == decision)
            and (regime is None or item.regime == regime)
        ]
        count = len(selected)
        if count < self.minimum_samples:
            return CalibrationEstimate(
                ready=False,
                sample_count=count,
                win_probability=None,
                expected_r=None,
                profit_factor=None,
                brier_score=None,
                lower_edge=round(lower, 4),
                upper_edge=round(upper, 4),
                reason=f"amostra insuficiente: {count}/{self.minimum_samples}",
            )

        wins = sum(1 for item in selected if item.won)
        # Laplace smoothing avoids 0%/100% certainty in small samples.
        probability = (wins + 1.0) / (count + 2.0)
        expected_r = sum(item.realized_r for item in selected) / count
        gross_profit = sum(item.realized_r for item in selected if item.realized_r > 0)
        gross_loss = abs(sum(item.realized_r for item in selected if item.realized_r < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else None
        brier = sum((probability - (1.0 if item.won else 0.0)) ** 2 for item in selected) / count
        return CalibrationEstimate(
            ready=True,
            sample_count=count,
            win_probability=round(probability, 6),
            expected_r=round(expected_r, 6),
            profit_factor=round(profit_factor, 6) if profit_factor is not None else None,
            brier_score=round(brier, 6),
            lower_edge=round(lower, 4),
            upper_edge=round(upper, 4),
            reason="estimativa historica concluida; ainda depende de validacao fora da amostra",
        )
