from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .domain import OperatingMode


class Settings(BaseSettings):
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
        for key in ("binance_api_key", "binance_api_secret", "telegram_bot_token"):
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
    return {
        "nexor_mode": system.get("mode", "PAPER"),
        "nexor_host": system.get("host", "127.0.0.1"),
        "nexor_port": system.get("port", 8809),
        "nexor_log_level": system.get("log_level", "INFO"),
        "nexor_database_path": system.get("database_path", "data/nexor_x.db"),
        "allow_live_mode": system.get("allow_live_mode", False),
        "binance_api_key": binance.get("api_key", ""),
        "binance_api_secret": binance.get("api_secret", ""),
        "binance_testnet": binance.get("testnet", False),
        "telegram_bot_token": telegram.get("bot_token", ""),
        "telegram_chat_id": telegram.get("chat_id", ""),
        "ollama_base_url": ollama.get("base_url", "http://127.0.0.1:11434"),
        "ollama_model": ollama.get("model", "llama3.2:3b"),
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(**_yaml_values())
