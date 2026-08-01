from __future__ import annotations
from functools import lru_cache
from pathlib import Path
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
            raise ValueError("LIVE blocked: laboratory certification is required.")
        if self.nexor_mode is OperatingMode.LIVE and (
            not self.binance_api_key or not self.binance_api_secret
        ):
            raise ValueError("Binance credentials are mandatory in LIVE mode.")
        return self

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
