from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
from typing import Any, Awaitable, Callable


@dataclass(frozen=True, slots=True)
class ShadowAdvance:
    closed: bool
    stop_price: float
    highest_price: float
    lowest_price: float
    partial_taken: bool
    remaining_fraction: float
    partial_net_r: float
    realized_r: float | None
    reason: str | None


class CausalShadowLearningService:
    """Creates calibration observations without bypassing the PAPER gate.

    Shadow positions never change portfolio equity and never call an exchange.
    Only a completed shadow position becomes a quant_observation. The same
    decision/regime/raw-edge fields consumed by CalibrationEngine are persisted.
    """

    def __init__(self, database: Any, *, quant_assessment: Any, market_state: Any,
                 symbols: tuple[str, ...], fee_rate: float, slippage_rate: float,
                 symbol_provider: Callable[[], Awaitable[tuple[str, ...]]] | None = None,
                 stop_loss_pct: float, break_even_trigger_r: float,
                 break_even_buffer_r: float, partial_trigger_r: float,
                 partial_fraction: float, trailing_start_r: float,
                 trailing_distance_r: float, maximum_holding_hours: float = 48.0) -> None:
        self.database = database
        self.quant_assessment = quant_assessment
        self.market_state = market_state
        self.symbols = symbols
        self.symbol_provider = symbol_provider
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate
        self.stop_loss_pct = stop_loss_pct
        self.break_even_trigger_r = break_even_trigger_r
        self.break_even_buffer_r = break_even_buffer_r
        self.partial_trigger_r = partial_trigger_r
        self.partial_fraction = partial_fraction
        self.trailing_start_r = trailing_start_r
        self.trailing_distance_r = trailing_distance_r
        self.maximum_holding_hours = maximum_holding_hours

    async def start(self) -> None:
        await self.database.execute("""
        CREATE TABLE IF NOT EXISTS causal_shadow_positions(
            symbol TEXT PRIMARY KEY, side TEXT NOT NULL, decision TEXT NOT NULL,
            regime TEXT NOT NULL, raw_edge REAL NOT NULL, entry_price REAL NOT NULL,
            stop_price REAL NOT NULL, highest_price REAL NOT NULL, lowest_price REAL NOT NULL,
            partial_taken INTEGER NOT NULL, remaining_fraction REAL NOT NULL,
            partial_net_r REAL NOT NULL, opened_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""")
        await self.database.execute("""
        CREATE TABLE IF NOT EXISTS causal_shadow_cycles(
            id INTEGER PRIMARY KEY AUTOINCREMENT, opened INTEGER NOT NULL,
            closed INTEGER NOT NULL, blocked INTEGER NOT NULL,
            payload_json TEXT NOT NULL, created_at TEXT NOT NULL
        )""")

    async def run_once(self) -> dict[str, Any]:
        await self.start()
        opened: list[str] = []
        closed: list[dict[str, Any]] = []
        blocked: list[dict[str, str]] = []
        symbols = await self.symbol_provider() if self.symbol_provider else self.symbols
        for symbol in symbols:
            try:
                market = await self.market_state(symbol)
                snapshot = market.get("snapshot") or {}
                if bool(snapshot.get("stale", True)):
                    blocked.append({"symbol": symbol, "reason": "STALE_MARKET"})
                    continue
                price = float(snapshot.get("price") or 0)
                if price <= 0:
                    blocked.append({"symbol": symbol, "reason": "INVALID_PRICE"})
                    continue
                position = await self._position(symbol)
                if position:
                    advance = self.advance_position(position, price)
                    if advance.closed:
                        await self._complete(position, advance)
                        closed.append({"symbol": symbol, "realized_r": advance.realized_r,
                                       "reason": advance.reason})
                    else:
                        await self._update(symbol, advance)
                    continue
                quant = await self.quant_assessment(symbol)
                decision = str(quant.get("decision") or "NO_EDGE")
                if decision not in {"LONG_BIAS", "SHORT_BIAS"}:
                    blocked.append({"symbol": symbol, "reason": "NO_DIRECTIONAL_EDGE"})
                    continue
                await self._open(symbol, price, decision, str(market.get("regime") or "UNKNOWN"),
                                 float(quant.get("raw_edge") or 0))
                opened.append(symbol)
            except Exception as exc:
                blocked.append({"symbol": symbol, "reason": f"ERROR:{type(exc).__name__}:{exc}"[:180]})
        created_at = datetime.now(UTC).isoformat()
        payload = {"status": "OK", "opened": opened, "closed": closed,
                   "blocked": blocked, "created_at": created_at,
                   "paper_orders_created": 0, "live_orders_created": 0}
        await self.database.execute(
            "INSERT INTO causal_shadow_cycles(opened,closed,blocked,payload_json,created_at) VALUES(?,?,?,?,?)",
            (len(opened), len(closed), len(blocked), json.dumps(payload, ensure_ascii=False), created_at),
        )
        return payload

    async def _position(self, symbol: str) -> dict[str, Any] | None:
        rows = await self.database.fetchall(
            "SELECT symbol,side,decision,regime,raw_edge,entry_price,stop_price,highest_price,"
            "lowest_price,partial_taken,remaining_fraction,partial_net_r,opened_at "
            "FROM causal_shadow_positions WHERE symbol=?", (symbol,))
        if not rows:
            return None
        keys = ("symbol","side","decision","regime","raw_edge","entry_price","stop_price",
                "highest_price","lowest_price","partial_taken","remaining_fraction",
                "partial_net_r","opened_at")
        return dict(zip(keys, rows[0]))

    async def _open(self, symbol: str, price: float, decision: str,
                    regime: str, raw_edge: float) -> None:
        side = "LONG" if decision == "LONG_BIAS" else "SHORT"
        entry = price*(1+self.slippage_rate if side == "LONG" else 1-self.slippage_rate)
        risk = entry*self.stop_loss_pct
        stop = entry-risk if side == "LONG" else entry+risk
        now = datetime.now(UTC).isoformat()
        await self.database.execute(
            "INSERT INTO causal_shadow_positions VALUES(?,?,?,?,?,?,?,?,?,0,1.0,0.0,?,?)",
            (symbol,side,decision,regime,raw_edge,entry,stop,entry,entry,now,now))

    async def _update(self, symbol: str, advance: ShadowAdvance) -> None:
        await self.database.execute(
            "UPDATE causal_shadow_positions SET stop_price=?,highest_price=?,lowest_price=?,"
            "partial_taken=?,remaining_fraction=?,partial_net_r=?,updated_at=? WHERE symbol=?",
            (advance.stop_price,advance.highest_price,advance.lowest_price,
             int(advance.partial_taken),advance.remaining_fraction,advance.partial_net_r,
             datetime.now(UTC).isoformat(),symbol))

    async def _complete(self, position: dict[str, Any], advance: ShadowAdvance) -> None:
        now = datetime.now(UTC).isoformat()
        await self.database.transaction([
            ("INSERT INTO quant_observations(symbol,decision,raw_edge,regime,realized_r,closed_at) "
             "VALUES(?,?,?,?,?,?)",
             (position["symbol"],position["decision"],float(position["raw_edge"]),
              position["regime"],float(advance.realized_r or 0),now)),
            ("DELETE FROM causal_shadow_positions WHERE symbol=?", (position["symbol"],)),
        ])

    def advance_position(self, position: dict[str, Any], market_price: float) -> ShadowAdvance:
        side = str(position["side"])
        entry = float(position["entry_price"])
        initial_risk = entry*self.stop_loss_pct
        stop = float(position["stop_price"])
        high = max(float(position["highest_price"]), market_price)
        low = min(float(position["lowest_price"]), market_price)
        partial = bool(position["partial_taken"])
        remaining = float(position["remaining_fraction"])
        partial_net = float(position["partial_net_r"])
        current_r = ((market_price-entry) if side == "LONG" else (entry-market_price))/initial_risk
        opened_at = position.get("opened_at")
        if opened_at:
            opened = datetime.fromisoformat(str(opened_at).replace("Z", "+00:00"))
            if opened.tzinfo is None:
                opened = opened.replace(tzinfo=UTC)
            age_hours = (datetime.now(UTC)-opened).total_seconds()/3600
            if age_hours >= self.maximum_holding_hours:
                exit_r = self._net_r(entry, market_price, side, remaining)
                return ShadowAdvance(True, stop, high, low, partial, 0.0, partial_net,
                                     partial_net+exit_r, "SHADOW_TIME_LIMIT")
        if (market_price <= stop if side == "LONG" else market_price >= stop):
            exit_r = self._net_r(entry, market_price, side, remaining)
            return ShadowAdvance(True, stop, high, low, partial, 0.0, partial_net,
                                 partial_net+exit_r, "PROTECTIVE_STOP")
        if current_r >= self.break_even_trigger_r:
            candidate = entry+(initial_risk*self.break_even_buffer_r if side == "LONG" else -initial_risk*self.break_even_buffer_r)
            stop = max(stop,candidate) if side == "LONG" else min(stop,candidate)
        if current_r >= self.partial_trigger_r and not partial:
            fraction = remaining*self.partial_fraction
            partial_net += self._net_r(entry, market_price, side, fraction)
            remaining -= fraction
            partial = True
        if current_r >= self.trailing_start_r:
            distance = initial_risk*self.trailing_distance_r
            candidate = high-distance if side == "LONG" else low+distance
            stop = max(stop,candidate) if side == "LONG" else min(stop,candidate)
        return ShadowAdvance(False, stop, high, low, partial, remaining, partial_net, None, None)

    def _net_r(self, entry: float, market: float, side: str, fraction: float) -> float:
        exit_price = market*(1-self.slippage_rate if side == "LONG" else 1+self.slippage_rate)
        gross = ((exit_price-entry) if side == "LONG" else (entry-exit_price))/(
            entry*self.stop_loss_pct)
        fee_r = (entry*self.fee_rate+exit_price*self.fee_rate)/(entry*self.stop_loss_pct)
        return fraction*(gross-fee_r)

    async def status(self) -> dict[str, Any]:
        await self.start()
        positions = await self.database.fetchall("SELECT symbol FROM causal_shadow_positions ORDER BY symbol")
        observations = await self.database.fetchall("SELECT COUNT(*) FROM quant_observations")
        return {"state": "READY", "open_shadow_symbols": [str(x[0]) for x in positions],
                "total_observations": int(observations[0][0]) if observations else 0,
                "paper_orders_created": 0, "live_orders_created": 0}
