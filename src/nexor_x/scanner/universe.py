from __future__ import annotations

from dataclasses import asdict, dataclass
from math import log1p
from typing import Iterable

from nexor_x.market.models import MarketSnapshot


@dataclass(frozen=True, slots=True)
class ShallowCandidate:
    symbol: str
    score: float
    quote_volume: float
    range_pct: float
    change_pct: float

    def to_dict(self) -> dict[str, float | str]:
        return asdict(self)


class ShallowUniverseSelector:
    """Cheap deterministic first stage, before expensive deep assessment."""

    def __init__(self, *, limit: int = 60, minimum_quote_volume: float = 1_000_000.0) -> None:
        if limit < 1:
            raise ValueError("shallow limit must be positive")
        self.limit = limit
        self.minimum_quote_volume = minimum_quote_volume

    def select(self, snapshots: Iterable[MarketSnapshot]) -> tuple[ShallowCandidate, ...]:
        eligible: list[ShallowCandidate] = []
        for item in snapshots:
            if item.stale or item.price <= 0 or item.open_price <= 0:
                continue
            if item.quote_volume < self.minimum_quote_volume:
                continue
            range_pct = max(0.0, (item.high_price-item.low_price)/item.open_price*100.0)
            if range_pct <= 0.05 or range_pct > 80.0:
                continue
            liquidity = min(log1p(item.quote_volume)/25.0, 1.0)
            useful_volatility = max(0.0, 1.0-abs(range_pct-4.0)/20.0)
            momentum = min(abs(item.price_change_percent)/15.0, 1.0)
            score = liquidity*0.60 + useful_volatility*0.25 + momentum*0.15
            eligible.append(ShallowCandidate(
                symbol=item.symbol, score=round(score, 8), quote_volume=item.quote_volume,
                range_pct=round(range_pct, 6), change_pct=item.price_change_percent,
            ))
        eligible.sort(key=lambda item: (-item.score, item.symbol))
        return tuple(eligible[:self.limit])
