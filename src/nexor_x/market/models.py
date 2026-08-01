from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class MarketRegime(StrEnum):
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    RANGE = "RANGE"
    COMPRESSION = "COMPRESSION"
    EXPANSION = "EXPANSION"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    symbol: str
    price: float
    open_price: float
    high_price: float
    low_price: float
    volume: float
    quote_volume: float
    price_change_percent: float
    fetched_at: datetime
    source: str
    stale: bool = False

    @property
    def intraday_range_percent(self) -> float:
        if self.open_price <= 0:
            return 0.0
        return ((self.high_price - self.low_price) / self.open_price) * 100.0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["fetched_at"] = self.fetched_at.astimezone(UTC).isoformat()
        data["intraday_range_percent"] = self.intraday_range_percent
        return data


@dataclass(frozen=True, slots=True)
class MarketState:
    symbol: str
    regime: MarketRegime
    direction: str
    momentum: float
    volatility: float
    confidence: float
    rationale: tuple[str, ...]
    snapshot: MarketSnapshot
    evaluated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "regime": self.regime.value,
            "direction": self.direction,
            "momentum": self.momentum,
            "volatility": self.volatility,
            "confidence": self.confidence,
            "rationale": list(self.rationale),
            "snapshot": self.snapshot.to_dict(),
            "evaluated_at": self.evaluated_at.astimezone(UTC).isoformat(),
        }
