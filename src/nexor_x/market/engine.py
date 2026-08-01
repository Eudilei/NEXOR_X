from __future__ import annotations

from datetime import UTC, datetime

from .models import MarketRegime, MarketSnapshot, MarketState


class MarketIntelligenceEngine:
    """Deterministic, explainable first-stage market-regime classifier.

    This is intentionally not a trading strategy. It only converts an observed
    market snapshot into a transparent state used later by evidence and strategy
    modules. Thresholds are configuration, not learned probabilities.
    """

    def classify(self, snapshot: MarketSnapshot) -> MarketState:
        change = snapshot.price_change_percent
        volatility = max(0.0, snapshot.intraday_range_percent)
        abs_change = abs(change)
        rationale: list[str] = []

        if volatility < 0.35 and abs_change < 0.20:
            regime = MarketRegime.COMPRESSION
            rationale.append("faixa intradiaria estreita")
        elif volatility >= 3.50:
            regime = MarketRegime.EXPANSION
            rationale.append("faixa intradiaria elevada")
        elif change >= 1.00:
            regime = MarketRegime.TREND_UP
            rationale.append("variacao diaria positiva relevante")
        elif change <= -1.00:
            regime = MarketRegime.TREND_DOWN
            rationale.append("variacao diaria negativa relevante")
        else:
            regime = MarketRegime.RANGE
            rationale.append("sem deslocamento direcional suficiente")

        if change > 0.15:
            direction = "UP"
        elif change < -0.15:
            direction = "DOWN"
        else:
            direction = "NEUTRAL"

        momentum = round(min(abs_change / 5.0, 1.0), 4)
        volatility_score = round(min(volatility / 6.0, 1.0), 4)
        confidence = self._confidence(snapshot, regime, momentum, volatility_score)
        if snapshot.stale:
            rationale.append("dados em cache marcados como desatualizados")

        return MarketState(
            symbol=snapshot.symbol,
            regime=regime,
            direction=direction,
            momentum=momentum,
            volatility=volatility_score,
            confidence=confidence,
            rationale=tuple(rationale),
            snapshot=snapshot,
            evaluated_at=datetime.now(UTC),
        )

    @staticmethod
    def _confidence(
        snapshot: MarketSnapshot,
        regime: MarketRegime,
        momentum: float,
        volatility: float,
    ) -> float:
        base = 0.45
        if regime in {MarketRegime.TREND_UP, MarketRegime.TREND_DOWN}:
            base += min(momentum * 0.35, 0.30)
        elif regime in {MarketRegime.COMPRESSION, MarketRegime.EXPANSION}:
            base += min(volatility * 0.30, 0.25)
        else:
            base += 0.10
        if snapshot.volume > 0 and snapshot.quote_volume > 0:
            base += 0.08
        if snapshot.stale:
            base -= 0.25
        return round(max(0.05, min(base, 0.95)), 4)
