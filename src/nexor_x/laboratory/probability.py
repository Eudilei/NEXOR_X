from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean
from typing import Iterable, Sequence

from .models import OutcomeObservation


@dataclass(frozen=True, slots=True)
class ProbabilityCalibrationReport:
    ready: bool
    method: str
    sample_count: int
    probability: float | None
    confidence_low_95: float | None
    confidence_high_95: float | None
    expected_r: float | None
    profit_factor: float | None
    brier_score: float | None
    expected_calibration_error: float | None
    fractional_kelly: float | None
    validation_brier: float | None
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "ready": self.ready,
            "method": self.method,
            "sample_count": self.sample_count,
            "probability": self.probability,
            "confidence_low_95": self.confidence_low_95,
            "confidence_high_95": self.confidence_high_95,
            "expected_r": self.expected_r,
            "profit_factor": self.profit_factor,
            "brier_score": self.brier_score,
            "expected_calibration_error": self.expected_calibration_error,
            "fractional_kelly": self.fractional_kelly,
            "validation_brier": self.validation_brier,
            "reason": self.reason,
            "execution_allowed": False,
            "live_certified": False,
        }


class ProbabilityCalibrationEngine:
    """Calibrates Quant Brain raw edge without external ML dependencies.

    Two candidate models are fitted on an earlier temporal partition and compared
    on a later holdout: Platt logistic scaling and isotonic regression (PAVA).
    The method with the lowest holdout Brier score is refitted on all samples.
    """

    def __init__(
        self,
        minimum_samples: int = 60,
        holdout_fraction: float = 0.25,
        ece_bins: int = 10,
        kelly_fraction: float = 0.25,
    ) -> None:
        if minimum_samples < 20:
            raise ValueError("minimum_samples must be at least 20")
        if not 0.15 <= holdout_fraction <= 0.40:
            raise ValueError("holdout_fraction must be between 0.15 and 0.40")
        if ece_bins < 5:
            raise ValueError("ece_bins must be at least 5")
        if not 0 < kelly_fraction <= 1:
            raise ValueError("kelly_fraction must be in (0, 1]")
        self.minimum_samples = minimum_samples
        self.holdout_fraction = holdout_fraction
        self.ece_bins = ece_bins
        self.kelly_fraction = kelly_fraction

    def calibrate(
        self,
        raw_edge: float,
        observations: Iterable[OutcomeObservation],
        *,
        decision: str,
        regime: str,
    ) -> ProbabilityCalibrationReport:
        selected = sorted(
            (
                item for item in observations
                if item.decision == decision and item.regime == regime
            ),
            key=lambda item: item.closed_at,
        )
        count = len(selected)
        if count < self.minimum_samples:
            return ProbabilityCalibrationReport(
                ready=False, method="NONE", sample_count=count,
                probability=None, confidence_low_95=None, confidence_high_95=None,
                expected_r=None, profit_factor=None, brier_score=None,
                expected_calibration_error=None, fractional_kelly=None,
                validation_brier=None,
                reason=f"amostra insuficiente: {count}/{self.minimum_samples}",
            )

        split = max(1, min(count - 1, int(count * (1.0 - self.holdout_fraction))))
        train, holdout = selected[:split], selected[split:]
        x_train = [item.raw_edge for item in train]
        y_train = [1.0 if item.won else 0.0 for item in train]
        x_hold = [item.raw_edge for item in holdout]
        y_hold = [1.0 if item.won else 0.0 for item in holdout]

        platt = self._fit_platt(x_train, y_train)
        iso = self._fit_isotonic(x_train, y_train)
        platt_hold = [self._predict_platt(platt, value) for value in x_hold]
        iso_hold = [self._predict_isotonic(iso, value) for value in x_hold]
        platt_brier = self._brier(platt_hold, y_hold)
        iso_brier = self._brier(iso_hold, y_hold)
        method = "ISOTONIC" if iso_brier + 1e-12 < platt_brier else "PLATT"
        validation_brier = min(platt_brier, iso_brier)

        x_all = [item.raw_edge for item in selected]
        y_all = [1.0 if item.won else 0.0 for item in selected]
        if method == "ISOTONIC":
            model = self._fit_isotonic(x_all, y_all)
            probability = self._predict_isotonic(model, raw_edge)
            fitted = [self._predict_isotonic(model, value) for value in x_all]
        else:
            model = self._fit_platt(x_all, y_all)
            probability = self._predict_platt(model, raw_edge)
            fitted = [self._predict_platt(model, value) for value in x_all]

        probability = self._clip_probability(probability)
        low, high = self._wilson_interval(probability, count)
        expected_r = mean(item.realized_r for item in selected)
        gross_profit = sum(item.realized_r for item in selected if item.realized_r > 0)
        gross_loss = abs(sum(item.realized_r for item in selected if item.realized_r < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else None
        brier = self._brier(fitted, y_all)
        ece = self._ece(fitted, y_all)
        avg_win = mean([item.realized_r for item in selected if item.realized_r > 0] or [0.0])
        avg_loss = abs(mean([item.realized_r for item in selected if item.realized_r < 0] or [-1.0]))
        payoff = avg_win / avg_loss if avg_loss > 0 else 0.0
        full_kelly = probability - ((1.0 - probability) / payoff) if payoff > 0 else 0.0
        fractional_kelly = max(0.0, min(1.0, full_kelly * self.kelly_fraction))

        return ProbabilityCalibrationReport(
            ready=True,
            method=method,
            sample_count=count,
            probability=round(probability, 6),
            confidence_low_95=round(low, 6),
            confidence_high_95=round(high, 6),
            expected_r=round(expected_r, 6),
            profit_factor=round(profit_factor, 6) if profit_factor is not None else None,
            brier_score=round(brier, 6),
            expected_calibration_error=round(ece, 6),
            fractional_kelly=round(fractional_kelly, 6),
            validation_brier=round(validation_brier, 6),
            reason="calibracao temporal concluida; uso operacional continua bloqueado ate certificacao",
        )

    @staticmethod
    def _clip_probability(value: float) -> float:
        return max(0.001, min(0.999, value))

    def _fit_platt(self, xs: Sequence[float], ys: Sequence[float]) -> tuple[float, float]:
        a, b = 0.0, math.log((sum(ys) + 1.0) / (len(ys) - sum(ys) + 1.0))
        for _ in range(250):
            grad_a = grad_b = 0.0
            for x, y in zip(xs, ys, strict=True):
                p = self._sigmoid(a * x + b)
                grad_a += (p - y) * x
                grad_b += p - y
            scale = max(1, len(xs))
            new_a = a - 0.15 * grad_a / scale
            new_b = b - 0.15 * grad_b / scale
            if abs(new_a - a) + abs(new_b - b) < 1e-9:
                break
            a, b = new_a, new_b
        return a, b

    @staticmethod
    def _sigmoid(value: float) -> float:
        if value >= 0:
            z = math.exp(-value)
            return 1.0 / (1.0 + z)
        z = math.exp(value)
        return z / (1.0 + z)

    def _predict_platt(self, model: tuple[float, float], value: float) -> float:
        return self._clip_probability(self._sigmoid(model[0] * value + model[1]))

    @staticmethod
    def _fit_isotonic(xs: Sequence[float], ys: Sequence[float]) -> list[tuple[float, float]]:
        ordered = sorted(zip(xs, ys, strict=True), key=lambda pair: pair[0])
        blocks: list[dict[str, float]] = []
        for x, y in ordered:
            blocks.append({"low": x, "high": x, "sum": y, "weight": 1.0})
            while len(blocks) >= 2:
                left, right = blocks[-2], blocks[-1]
                if left["sum"] / left["weight"] <= right["sum"] / right["weight"]:
                    break
                merged = {
                    "low": left["low"], "high": right["high"],
                    "sum": left["sum"] + right["sum"],
                    "weight": left["weight"] + right["weight"],
                }
                blocks[-2:] = [merged]
        return [(block["high"], block["sum"] / block["weight"]) for block in blocks]

    def _predict_isotonic(self, model: Sequence[tuple[float, float]], value: float) -> float:
        for threshold, probability in model:
            if value <= threshold:
                return self._clip_probability(probability)
        return self._clip_probability(model[-1][1])

    @staticmethod
    def _brier(probabilities: Sequence[float], outcomes: Sequence[float]) -> float:
        if not probabilities:
            return 1.0
        return sum((p - y) ** 2 for p, y in zip(probabilities, outcomes, strict=True)) / len(probabilities)

    def _ece(self, probabilities: Sequence[float], outcomes: Sequence[float]) -> float:
        total = len(probabilities)
        error = 0.0
        for index in range(self.ece_bins):
            low = index / self.ece_bins
            high = (index + 1) / self.ece_bins
            indexes = [i for i, p in enumerate(probabilities) if low <= p < high or (index == self.ece_bins - 1 and p == 1.0)]
            if not indexes:
                continue
            confidence = mean(probabilities[i] for i in indexes)
            accuracy = mean(outcomes[i] for i in indexes)
            error += len(indexes) / total * abs(confidence - accuracy)
        return error

    @staticmethod
    def _wilson_interval(probability: float, count: int) -> tuple[float, float]:
        z = 1.959963984540054
        denominator = 1.0 + z * z / count
        center = (probability + z * z / (2.0 * count)) / denominator
        margin = z * math.sqrt((probability * (1.0 - probability) + z * z / (4.0 * count)) / count) / denominator
        return max(0.0, center - margin), min(1.0, center + margin)
