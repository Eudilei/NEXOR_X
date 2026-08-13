from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .domain import OperatingMode


class Settings(BaseSettings):
    certification_minimum_paper_trades: int = 1000
    certification_minimum_profit_factor: float = 1.40
    certification_minimum_expected_r: float = 0.05
    certification_maximum_drawdown_pct: float = 15.0
    certification_minimum_walk_forward_pass_ratio: float = 0.70
    certification_maximum_ruin_probability: float = 0.02
    certification_maximum_brier_score_oos: float = 0.24
    certification_maximum_ece_oos: float = 0.08
    certification_minimum_days_in_paper: int = 30
    certification_minimum_recent_profit_factor: float = 1.15
    certification_minimum_recent_expected_r: float = 0.01

    binance_live_base_url: str = "https://fapi.binance.com"
    binance_testnet_base_url: str = "https://testnet.binancefuture.com"
    binance_live_timeout_seconds: float = 10.0
    binance_recv_window_ms: int = 5000
    binance_maximum_time_drift_ms: int = 1000
    binance_use_testnet: bool = True

    pretrade_backtest_minimum_samples: int = 30
    pretrade_backtest_maximum_samples: int = 300
    pretrade_backtest_minimum_profit_factor: float = 1.10
    pretrade_backtest_minimum_expected_r: float = 0.05
    pretrade_backtest_minimum_recent_profit_factor: float = 1.00
    pretrade_backtest_minimum_recent_expected_r: float = 0.00
    pretrade_backtest_maximum_drawdown_r: float = 8.0
    pretrade_backtest_minimum_walk_forward_pass_ratio: float = 0.60
    pretrade_backtest_folds: int = 3

    ollama_autostart: bool = True
    ollama_command: str = "ollama"
    cloudflared_enabled: bool = True
    cloudflared_command: str = "cloudflared"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    nexor_mode: OperatingMode = OperatingMode.PAPER
    nexor_host: str = "127.0.0.1"
    nexor_port: int = Field(default=8809, ge=1024, le=65535)
    nexor_log_level: str = "INFO"
    nexor_database_path: Path = Path("data/nexor_x.db")
    binance_api_key: str = ""
    binance_api_secret: str = ""
    binance_testnet: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2:3b"
    allow_live_mode: bool = False
    admin_api_token: str = ""
    market_cache_ttl_seconds: float = Field(default=15.0, ge=1.0, le=300.0)
    market_stale_after_seconds: float = Field(default=120.0, ge=10.0, le=3600.0)
    market_failure_cooldown_seconds: float = Field(default=60.0, ge=5.0, le=900.0)
    initial_paper_equity: float = Field(default=100.0, gt=0)
    risk_per_trade_pct: float = Field(default=10.0, gt=0, le=100)
    leverage: float = Field(default=15.0, ge=1.0, le=125.0)
    max_open_positions: int = Field(default=10, ge=1, le=100)
    hard_stop_drawdown_pct: float = Field(default=25.0, gt=0, le=100)
    minimum_expected_r: float = Field(default=0.05, ge=-10, le=10)
    minimum_profit_factor: float = Field(default=1.10, ge=0, le=100)
    minimum_calibration_samples: int = Field(default=30, ge=5, le=100000)
    paper_fee_rate: float = Field(default=0.0005, ge=0, lt=1)
    paper_slippage_rate: float = Field(default=0.0003, ge=0, lt=1)
    paper_stop_loss_pct: float = Field(default=0.01, gt=0, lt=1)
    scanner_enabled: bool = True
    scanner_symbols: str = "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT"
    scanner_interval_seconds: float = Field(default=60.0, ge=15.0, le=86400.0)
    scanner_concurrency: int = Field(default=4, ge=1, le=32)
    scanner_top_candidates: int = Field(default=10, ge=1, le=100)
    position_break_even_trigger_r: float = Field(default=0.8, gt=0, le=20)
    position_break_even_buffer_r: float = Field(default=0.05, ge=0, le=5)
    position_partial_trigger_r: float = Field(default=1.5, gt=0, le=50)
    position_partial_fraction: float = Field(default=0.35, gt=0, lt=1)
    position_trailing_start_r: float = Field(default=2.0, gt=0, le=50)
    position_trailing_distance_r: float = Field(default=0.8, gt=0, le=20)
    edge_discovery_maximum_fdr: float = Field(default=0.10, gt=0, le=0.50)
    probability_minimum_samples: int = Field(default=60, ge=20, le=100000)
    probability_holdout_fraction: float = Field(default=0.25, ge=0.15, le=0.40)
    probability_kelly_fraction: float = Field(default=0.25, gt=0, le=1.0)
    monte_carlo_minimum_observations: int = Field(default=60, ge=20, le=100000)
    monte_carlo_simulations: int = Field(default=5000, ge=100, le=100000)
    monte_carlo_horizon_trades: int = Field(default=250, ge=20, le=100000)
    monte_carlo_block_size: int = Field(default=10, ge=1, le=10000)
    monte_carlo_ruin_drawdown_pct: float = Field(default=25.0, gt=0, le=100)
    monte_carlo_seed: int = 20260803
    walk_forward_folds: int = Field(default=5, ge=2, le=20)
    walk_forward_minimum_train_observations: int = Field(default=60, ge=20, le=100000)
    walk_forward_minimum_test_observations: int = Field(default=20, ge=5, le=100000)
    walk_forward_minimum_pass_ratio: float = Field(default=0.60, gt=0, le=1)
    walk_forward_minimum_profit_factor: float = Field(default=1.05, ge=0, le=100)
    counterfactual_minimum_observations: int = Field(default=60, ge=20, le=100000)
    counterfactual_minimum_kept_observations: int = Field(default=20, ge=5, le=100000)
    counterfactual_edge_thresholds: str = "0.10,0.20,0.30,0.40,0.50"
    allocation_maximum_candidates: int = 5
    allocation_maximum_weight_per_candidate: float = 0.35
    allocation_maximum_weight_per_correlation_group: float = 0.55
    allocation_minimum_score: float = 0.20
    allocation_maximum_ruin_probability: float = 0.05
    allocation_maximum_candidate_drawdown_r: float = 8.0
    allocation_recovery_drawdown_trigger_pct: float = 10.0
    allocation_recovery_risk_multiplier: float = 0.35

    @property
    def counterfactual_edge_threshold_list(self) -> tuple[float, ...]:
        return tuple(float(item.strip()) for item in self.counterfactual_edge_thresholds.split(",") if item.strip())

    @property
    def scanner_symbol_list(self) -> tuple[str, ...]:
        return tuple(item.strip().upper() for item in self.scanner_symbols.split(",") if item.strip())

    @model_validator(mode="after")
    def live_guard(self) -> "Settings":
        if self.nexor_mode is OperatingMode.LIVE and not self.allow_live_mode:
            raise ValueError("LIVE bloqueado: certificacao do laboratorio e obrigatoria.")
        if self.nexor_mode is OperatingMode.LIVE and (
            not self.binance_api_key or not self.binance_api_secret
        ):
            raise ValueError("Credenciais Binance sao obrigatorias em LIVE.")
        return self

    def public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        for key in ("binance_api_key", "binance_api_secret", "telegram_bot_token", "admin_api_token"):
            data[key] = "***" if data.get(key) else ""
        return data


def _yaml_values(path: Path = Path("config/settings.yaml")) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    system = raw.get("system", {})
    binance = raw.get("binance", {})
    telegram = raw.get("telegram", {})
    ollama = raw.get("ollama", {})
    market = raw.get("market", {})
    risk = raw.get("risk", {})
    scanner = raw.get("scanner", {})
    position = raw.get("position_management", {})
    discovery = raw.get("edge_discovery", {})
    probability = raw.get("probability_calibration", {})
    monte_carlo = raw.get("monte_carlo", {})
    walk_forward = raw.get("walk_forward", {})
    counterfactual = raw.get("counterfactual", {})
    return {
        "nexor_mode": system.get("mode", "PAPER"),
        "nexor_host": system.get("host", "127.0.0.1"),
        "nexor_port": system.get("port", 8809),
        "nexor_log_level": system.get("log_level", "INFO"),
        "nexor_database_path": system.get("database_path", "data/nexor_x.db"),
        "allow_live_mode": system.get("allow_live_mode", False),
        "admin_api_token": system.get("admin_api_token", ""),
        "binance_api_key": binance.get("api_key", ""),
        "binance_api_secret": binance.get("api_secret", ""),
        "binance_testnet": binance.get("testnet", False),
        "telegram_bot_token": telegram.get("bot_token", ""),
        "telegram_chat_id": telegram.get("chat_id", ""),
        "ollama_base_url": ollama.get("base_url", "http://127.0.0.1:11434"),
        "ollama_model": ollama.get("model", "llama3.2:3b"),
        "market_cache_ttl_seconds": market.get("cache_ttl_seconds", 15.0),
        "market_stale_after_seconds": market.get("stale_after_seconds", 120.0),
        "market_failure_cooldown_seconds": market.get("failure_cooldown_seconds", 60.0),
        "initial_paper_equity": risk.get("initial_paper_equity", 100.0),
        "risk_per_trade_pct": risk.get("risk_per_trade_pct", 10.0),
        "leverage": risk.get("leverage", 15.0),
        "max_open_positions": risk.get("max_open_positions", 10),
        "hard_stop_drawdown_pct": risk.get("hard_stop_drawdown_pct", 25.0),
        "minimum_expected_r": risk.get("minimum_expected_r", 0.05),
        "minimum_profit_factor": risk.get("minimum_profit_factor", 1.10),
        "minimum_calibration_samples": risk.get("minimum_calibration_samples", 30),
        "paper_fee_rate": risk.get("paper_fee_rate", 0.0005),
        "paper_slippage_rate": risk.get("paper_slippage_rate", 0.0003),
        "paper_stop_loss_pct": risk.get("paper_stop_loss_pct", 0.01),
        "scanner_enabled": scanner.get("enabled", True),
        "scanner_symbols": scanner.get("symbols", "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT"),
        "scanner_interval_seconds": scanner.get("interval_seconds", 60.0),
        "scanner_concurrency": scanner.get("concurrency", 4),
        "scanner_top_candidates": scanner.get("top_candidates", 10),
        "position_break_even_trigger_r": position.get("break_even_trigger_r", 0.8),
        "position_break_even_buffer_r": position.get("break_even_buffer_r", 0.05),
        "position_partial_trigger_r": position.get("partial_trigger_r", 1.5),
        "position_partial_fraction": position.get("partial_fraction", 0.35),
        "position_trailing_start_r": position.get("trailing_start_r", 2.0),
        "position_trailing_distance_r": position.get("trailing_distance_r", 0.8),
        "edge_discovery_maximum_fdr": discovery.get("maximum_fdr", 0.10),
        "probability_minimum_samples": probability.get("minimum_samples", 60),
        "probability_holdout_fraction": probability.get("holdout_fraction", 0.25),
        "probability_kelly_fraction": probability.get("kelly_fraction", 0.25),
        "monte_carlo_minimum_observations": monte_carlo.get("minimum_observations", 60),
        "monte_carlo_simulations": monte_carlo.get("simulations", 5000),
        "monte_carlo_horizon_trades": monte_carlo.get("horizon_trades", 250),
        "monte_carlo_block_size": monte_carlo.get("block_size", 10),
        "monte_carlo_ruin_drawdown_pct": monte_carlo.get("ruin_drawdown_pct", 25.0),
        "monte_carlo_seed": monte_carlo.get("seed", 20260803),
        "walk_forward_folds": walk_forward.get("folds", 5),
        "walk_forward_minimum_train_observations": walk_forward.get("minimum_train_observations", 60),
        "walk_forward_minimum_test_observations": walk_forward.get("minimum_test_observations", 20),
        "walk_forward_minimum_pass_ratio": walk_forward.get("minimum_pass_ratio", 0.60),
        "walk_forward_minimum_profit_factor": walk_forward.get("minimum_profit_factor", 1.05),
        "counterfactual_minimum_observations": counterfactual.get("minimum_observations", 60),
        "counterfactual_minimum_kept_observations": counterfactual.get("minimum_kept_observations", 20),
        "counterfactual_edge_thresholds": counterfactual.get("edge_thresholds", "0.10,0.20,0.30,0.40,0.50"),
    }


def _environment_overrides() -> dict[str, Any]:
    """Return explicit runtime overrides, including the hosting provider PORT."""
    mapping = {
        "NEXOR_MODE": "nexor_mode",
        "NEXOR_HOST": "nexor_host",
        "NEXOR_PORT": "nexor_port",
        "NEXOR_LOG_LEVEL": "nexor_log_level",
        "NEXOR_DATABASE_PATH": "nexor_database_path",
        "BINANCE_API_KEY": "binance_api_key",
        "BINANCE_API_SECRET": "binance_api_secret",
        "BINANCE_TESTNET": "binance_testnet",
        "TELEGRAM_BOT_TOKEN": "telegram_bot_token",
        "TELEGRAM_CHAT_ID": "telegram_chat_id",
        "OLLAMA_BASE_URL": "ollama_base_url",
        "OLLAMA_MODEL": "ollama_model",
        "ALLOW_LIVE_MODE": "allow_live_mode",
        "NEXOR_ADMIN_API_TOKEN": "admin_api_token",
        "MARKET_CACHE_TTL_SECONDS": "market_cache_ttl_seconds",
        "MARKET_STALE_AFTER_SECONDS": "market_stale_after_seconds",
        "MARKET_FAILURE_COOLDOWN_SECONDS": "market_failure_cooldown_seconds",
        "INITIAL_PAPER_EQUITY": "initial_paper_equity",
        "RISK_PER_TRADE_PCT": "risk_per_trade_pct",
        "LEVERAGE": "leverage",
        "MAX_OPEN_POSITIONS": "max_open_positions",
        "HARD_STOP_DRAWDOWN_PCT": "hard_stop_drawdown_pct",
        "MINIMUM_EXPECTED_R": "minimum_expected_r",
        "MINIMUM_PROFIT_FACTOR": "minimum_profit_factor",
        "MINIMUM_CALIBRATION_SAMPLES": "minimum_calibration_samples",
        "PAPER_FEE_RATE": "paper_fee_rate",
        "PAPER_SLIPPAGE_RATE": "paper_slippage_rate",
        "PAPER_STOP_LOSS_PCT": "paper_stop_loss_pct",
        "SCANNER_ENABLED": "scanner_enabled",
        "SCANNER_SYMBOLS": "scanner_symbols",
        "SCANNER_INTERVAL_SECONDS": "scanner_interval_seconds",
        "SCANNER_CONCURRENCY": "scanner_concurrency",
        "SCANNER_TOP_CANDIDATES": "scanner_top_candidates",
        "POSITION_BREAK_EVEN_TRIGGER_R": "position_break_even_trigger_r",
        "POSITION_BREAK_EVEN_BUFFER_R": "position_break_even_buffer_r",
        "POSITION_PARTIAL_TRIGGER_R": "position_partial_trigger_r",
        "POSITION_PARTIAL_FRACTION": "position_partial_fraction",
        "POSITION_TRAILING_START_R": "position_trailing_start_r",
        "POSITION_TRAILING_DISTANCE_R": "position_trailing_distance_r",
        "EDGE_DISCOVERY_MAXIMUM_FDR": "edge_discovery_maximum_fdr",
        "PROBABILITY_MINIMUM_SAMPLES": "probability_minimum_samples",
        "PROBABILITY_HOLDOUT_FRACTION": "probability_holdout_fraction",
        "PROBABILITY_KELLY_FRACTION": "probability_kelly_fraction",
        "MONTE_CARLO_MINIMUM_OBSERVATIONS": "monte_carlo_minimum_observations",
        "MONTE_CARLO_SIMULATIONS": "monte_carlo_simulations",
        "MONTE_CARLO_HORIZON_TRADES": "monte_carlo_horizon_trades",
        "MONTE_CARLO_BLOCK_SIZE": "monte_carlo_block_size",
        "MONTE_CARLO_RUIN_DRAWDOWN_PCT": "monte_carlo_ruin_drawdown_pct",
        "MONTE_CARLO_SEED": "monte_carlo_seed",
        "WALK_FORWARD_FOLDS": "walk_forward_folds",
        "WALK_FORWARD_MINIMUM_TRAIN_OBSERVATIONS": "walk_forward_minimum_train_observations",
        "WALK_FORWARD_MINIMUM_TEST_OBSERVATIONS": "walk_forward_minimum_test_observations",
        "WALK_FORWARD_MINIMUM_PASS_RATIO": "walk_forward_minimum_pass_ratio",
        "WALK_FORWARD_MINIMUM_PROFIT_FACTOR": "walk_forward_minimum_profit_factor",
        "COUNTERFACTUAL_MINIMUM_OBSERVATIONS": "counterfactual_minimum_observations",
        "COUNTERFACTUAL_MINIMUM_KEPT_OBSERVATIONS": "counterfactual_minimum_kept_observations",
        "COUNTERFACTUAL_EDGE_THRESHOLDS": "counterfactual_edge_thresholds",
    }
    values: dict[str, Any] = {}
    for env_name, field_name in mapping.items():
        value = os.getenv(env_name)
        if value is not None and value != "":
            values[field_name] = value
    if os.getenv("PORT"):
        values["nexor_port"] = os.environ["PORT"]
    return values


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    values = _yaml_values()
    values.update(_environment_overrides())
    return Settings(**values)
