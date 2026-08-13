from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ExternalCredentialsStatus:
    binance_api_key_configured: bool
    binance_api_secret_configured: bool
    telegram_bot_token_configured: bool
    telegram_chat_id_configured: bool

    @property
    def binance_ready(self) -> bool:
        return (
            self.binance_api_key_configured
            and self.binance_api_secret_configured
        )

    @property
    def telegram_ready(self) -> bool:
        return (
            self.telegram_bot_token_configured
            and self.telegram_chat_id_configured
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "binance": {
                "api_key_configured": self.binance_api_key_configured,
                "api_secret_configured": self.binance_api_secret_configured,
                "ready": self.binance_ready,
            },
            "telegram": {
                "bot_token_configured": self.telegram_bot_token_configured,
                "chat_id_configured": self.telegram_chat_id_configured,
                "ready": self.telegram_ready,
            },
            "secrets_exposed": False,
            "live_enabled": False,
        }


class ExternalCredentialsStatusService:
    """Reports only whether credentials exist.

    Secret values are never returned by this service.
    """

    def __init__(self, settings: Any) -> None:
        self.settings = settings

    async def status(self) -> dict[str, Any]:
        result = ExternalCredentialsStatus(
            binance_api_key_configured=bool(
                str(getattr(self.settings, "binance_api_key", "") or "").strip()
            ),
            binance_api_secret_configured=bool(
                str(getattr(self.settings, "binance_api_secret", "") or "").strip()
            ),
            telegram_bot_token_configured=bool(
                str(getattr(self.settings, "telegram_bot_token", "") or "").strip()
            ),
            telegram_chat_id_configured=bool(
                str(getattr(self.settings, "telegram_chat_id", "") or "").strip()
            ),
        )
        return result.to_dict()
