from __future__ import annotations

from nexor_x.market.models import MarketRegime, MarketState

from .models import Evidence, EvidenceDirection


class EvidenceEngine:
    """Transforms transparent market state into independent evidence records.

    The engine does not issue orders and does not claim calibrated probabilities.
    Each evidence record exposes its source and rationale for later attribution.
    """

    def evaluate(self, state: MarketState) -> tuple[Evidence, ...]:
        snapshot = state.snapshot
        evidences: list[Evidence] = []

        if state.direction == "UP":
            direction = EvidenceDirection.BULLISH
        elif state.direction == "DOWN":
            direction = EvidenceDirection.BEARISH
        else:
            direction = EvidenceDirection.NEUTRAL
        evidences.append(
            Evidence(
                name="price_momentum",
                direction=direction,
                strength=min(abs(snapshot.price_change_percent) / 5.0, 1.0),
                reliability=self._freshness_reliability(snapshot.stale),
                rationale=f"variacao de 24h em {snapshot.price_change_percent:.3f}%",
                source_fields=("price_change_percent",),
            )
        )

        regime_direction = EvidenceDirection.NEUTRAL
        if state.regime is MarketRegime.TREND_UP:
            regime_direction = EvidenceDirection.BULLISH
        elif state.regime is MarketRegime.TREND_DOWN:
            regime_direction = EvidenceDirection.BEARISH
        regime_strength = {
            MarketRegime.TREND_UP: 0.75,
            MarketRegime.TREND_DOWN: 0.75,
            MarketRegime.EXPANSION: 0.45,
            MarketRegime.COMPRESSION: 0.20,
            MarketRegime.RANGE: 0.10,
            MarketRegime.UNKNOWN: 0.0,
        }[state.regime]
        evidences.append(
            Evidence(
                name="market_regime",
                direction=regime_direction,
                strength=regime_strength,
                reliability=state.confidence,
                rationale=f"regime classificado como {state.regime.value}",
                source_fields=("regime", "confidence"),
            )
        )

        volume_ratio = 0.0
        if snapshot.volume > 0 and snapshot.quote_volume > 0 and snapshot.price > 0:
            expected_quote = snapshot.volume * snapshot.price
            volume_ratio = min(snapshot.quote_volume / expected_quote, 2.0)
        evidences.append(
            Evidence(
                name="volume_consistency",
                direction=EvidenceDirection.NEUTRAL,
                strength=min(abs(volume_ratio - 1.0), 1.0),
                reliability=self._freshness_reliability(snapshot.stale),
                rationale=f"consistencia entre volume base e volume cotado: {volume_ratio:.3f}",
                source_fields=("volume", "quote_volume", "price"),
            )
        )

        volatility_direction = EvidenceDirection.NEUTRAL
        volatility_strength = state.volatility
        evidences.append(
            Evidence(
                name="volatility_condition",
                direction=volatility_direction,
                strength=volatility_strength,
                reliability=self._freshness_reliability(snapshot.stale),
                rationale=f"volatilidade normalizada em {state.volatility:.4f}",
                source_fields=("intraday_range_percent",),
            )
        )

        return tuple(evidences)

    @staticmethod
    def _freshness_reliability(stale: bool) -> float:
        return 0.35 if stale else 0.85
