from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from .idempotency import IdempotencyRegistry, OrderIntent
from .models import TestnetOrderRequest, TestnetOrderResult


class TestnetOrderService:
    """Creates idempotent TESTNET orders only.

    The provided connector must be configured with use_testnet=True.
    """

    def __init__(self, database: Any, connector: Any) -> None:
        self.database = database
        self.connector = connector
        self.registry = IdempotencyRegistry(database)

    async def start(self) -> None:
        await self.registry.start()

    async def create(
        self,
        *,
        strategy_id: str,
        signal_id: str,
        request: TestnetOrderRequest,
    ) -> dict[str, Any]:
        if not getattr(self.connector.policy, "use_testnet", False):
            raise RuntimeError("TESTNET order service refuses non-testnet connector")

        normalized = request.normalized()
        intent = OrderIntent(
            strategy_id=strategy_id,
            signal_id=signal_id,
            request=normalized,
        )
        key = intent.key()
        existing = await self.registry.get(key)
        if existing is not None:
            result = TestnetOrderResult(
                status=existing["status"],
                idempotency_key=key,
                client_order_id=existing["client_order_id"],
                exchange_order_id=existing["exchange_order_id"],
                request=normalized,
                duplicate=True,
                testnet=True,
            )
            return result.to_dict()

        client_order_id = normalized.client_order_id or f"NX-{key[:28]}"
        created_at = datetime.now(UTC)
        payload_json = json.dumps(
            {
                "strategy_id": strategy_id,
                "signal_id": signal_id,
                "request": normalized.to_dict(),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        reserved = await self.registry.reserve(
            key=key,
            client_order_id=client_order_id,
            payload_json=payload_json,
            created_at=created_at.isoformat(),
        )
        if not reserved:
            existing = await self.registry.get(key)
            if existing is None:
                raise RuntimeError("idempotency reservation failed")
            return TestnetOrderResult(
                status=existing["status"],
                idempotency_key=key,
                client_order_id=existing["client_order_id"],
                exchange_order_id=existing["exchange_order_id"],
                request=normalized,
                duplicate=True,
                testnet=True,
            ).to_dict()

        try:
            response = await self.connector.create_testnet_order(
                symbol=normalized.symbol,
                side=normalized.side.value,
                order_type=normalized.order_type.value,
                quantity=normalized.quantity,
                price=normalized.price,
                reduce_only=normalized.reduce_only,
                client_order_id=client_order_id,
            )
            exchange_order_id = str(response.get("orderId"))
            status = str(response.get("status", "SUBMITTED"))
            await self.registry.finalize(
                key=key,
                exchange_order_id=exchange_order_id,
                status=status,
            )
        except Exception:
            await self.registry.finalize(
                key=key,
                exchange_order_id=None,
                status="FAILED",
            )
            raise

        return TestnetOrderResult(
            status=status,
            idempotency_key=key,
            client_order_id=client_order_id,
            exchange_order_id=exchange_order_id,
            request=normalized,
            duplicate=False,
            testnet=True,
        ).to_dict()
