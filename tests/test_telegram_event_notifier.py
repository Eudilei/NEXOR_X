from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from nexor_x.notifications import TelegramEventNotifier


@dataclass
class FakeEvent:
    topic: str
    payload: dict[str, Any] = field(default_factory=dict)


class FakeTelegram:
    def __init__(self) -> None:
        self.messages = []

    async def send(self, message: str) -> bool:
        self.messages.append(message)
        return True


@pytest.mark.asyncio
async def test_paper_open_notification() -> None:
    telegram = FakeTelegram()
    notifier = TelegramEventNotifier(telegram)

    await notifier.handle(
        FakeEvent(
            "execution.paper_open",
            {
                "symbol": "BTCUSDT",
                "side": "LONG",
                "price": 62000,
                "quantity": 0.01,
                "stop_price": 61000,
            },
        )
    )

    assert len(telegram.messages) == 1
    message = telegram.messages[0]
    assert "ENTRADA EM SIMULAÇÃO" in message
    assert "BTCUSDT" in message
    assert "COMPRA" in message


@pytest.mark.asyncio
async def test_no_spam_when_auto_cycle_did_nothing() -> None:
    telegram = FakeTelegram()
    notifier = TelegramEventNotifier(telegram)

    await notifier.handle(
        FakeEvent(
            "execution.auto_paper_cycle",
            {
                "opened_positions": 0,
                "errors": 0,
            },
        )
    )

    assert telegram.messages == []


@pytest.mark.asyncio
async def test_position_management_only_notifies_actions() -> None:
    telegram = FakeTelegram()
    notifier = TelegramEventNotifier(telegram)

    await notifier.handle(
        FakeEvent(
            "position.auto_management_cycle",
            {
                "evaluated_positions": 2,
                "action_count": 1,
                "closed_positions": 0,
            },
        )
    )

    assert "Ações de proteção: 1" in telegram.messages[0]


@pytest.mark.asyncio
async def test_disabled_notifier_does_not_send() -> None:
    telegram = FakeTelegram()
    notifier = TelegramEventNotifier(telegram, enabled=False)

    await notifier.handle(FakeEvent("system.started", {"mode": "PAPER"}))
    assert telegram.messages == []


def test_messages_never_need_secret_fields() -> None:
    notifier = TelegramEventNotifier(FakeTelegram())
    message = notifier._format(
        FakeEvent(
            "system.started",
            {
                "mode": "PAPER",
                "telegram_bot_token": "secret-token",
                "binance_api_secret": "secret-key",
            },
        )
    )
    assert message is not None
    assert "secret-token" not in message
    assert "secret-key" not in message
