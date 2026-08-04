from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def patch_kernel() -> None:
    path = ROOT / "src/nexor_x/kernel.py"
    text = path.read_text(encoding="utf-8")

    if "from nexor_x.exchange import BinanceCredentials, BinanceLiveConnector, BinanceLivePolicy" not in text:
        marker = "from nexor_x.position.service import PositionPolicy\n"
        if marker not in text:
            raise RuntimeError("Kernel import marker not found")
        text = text.replace(
            marker,
            marker
            + "from nexor_x.exchange import (\n"
            + "    BinanceCredentials,\n"
            + "    BinanceLiveConnector,\n"
            + "    BinanceLivePolicy,\n"
            + ")\n",
            1,
        )

    if "self.binance_live = BinanceLiveConnector(" not in text:
        marker = "        self.scanner = MarketScannerService(\n"
        if marker not in text:
            raise RuntimeError("Kernel scanner marker not found")
        block = (
            "        self.binance_live = BinanceLiveConnector(\n"
            "            BinanceCredentials(\n"
            "                api_key=settings.binance_api_key,\n"
            "                api_secret=settings.binance_api_secret,\n"
            "            ),\n"
            "            BinanceLivePolicy(\n"
            "                base_url=settings.binance_live_base_url,\n"
            "                testnet_url=settings.binance_testnet_base_url,\n"
            "                timeout_seconds=settings.binance_live_timeout_seconds,\n"
            "                recv_window_ms=settings.binance_recv_window_ms,\n"
            "                maximum_time_drift_ms=settings.binance_maximum_time_drift_ms,\n"
            "                use_testnet=settings.binance_use_testnet,\n"
            "            ),\n"
            "        )\n"
        )
        text = text.replace(marker, block + marker, 1)

    if "await self.binance_live.start()" not in text:
        marker = "        await self.portfolio.ensure_account()\n"
        if marker not in text:
            raise RuntimeError("Kernel startup marker not found")
        text = text.replace(
            marker,
            marker + "        await self.binance_live.start()\n",
            1,
        )

    if "await self.binance_live.stop()" not in text:
        marker = "        await self.telegram.stop()\n"
        if marker in text:
            text = text.replace(
                marker,
                "        await self.binance_live.stop()\n" + marker,
                1,
            )

    if "async def binance_live_readiness" not in text:
        marker = "    async def portfolio_status(self) -> dict[str, object]:\n"
        if marker not in text:
            raise RuntimeError("portfolio_status marker not found")
        methods = (
            "    async def binance_live_readiness(self) -> dict[str, object]:\n"
            "        report = await self.binance_live.readiness()\n"
            "        result = report.to_dict()\n"
            "        await self.event_bus.publish(Event(\n"
            "            'exchange.live_readiness',\n"
            "            {\n"
            "                'status': result['status'],\n"
            "                'testnet': result['testnet'],\n"
            "                'live_order_permission': False,\n"
            "            },\n"
            "            'binance_live_connector',\n"
            "        ))\n"
            "        return result\n\n"
        )
        text = text.replace(marker, methods + marker, 1)

    path.write_text(text, encoding="utf-8")


def patch_api() -> None:
    path = ROOT / "src/nexor_x/api/app.py"
    text = path.read_text(encoding="utf-8")

    if '@app.get("/api/exchange/live-readiness")' not in text:
        marker = '    @app.get("/api/portfolio/status")\n'
        if marker not in text:
            raise RuntimeError("API portfolio marker not found")
        endpoint = (
            '    @app.get("/api/exchange/live-readiness")\n'
            "    async def exchange_live_readiness(\n"
            "        _: None = Depends(require_admin),\n"
            "    ) -> dict[str, Any]:\n"
            "        return await kernel.binance_live_readiness()\n\n"
        )
        text = text.replace(marker, endpoint + marker, 1)

    path.write_text(text, encoding="utf-8")


def patch_config() -> None:
    path = ROOT / "src/nexor_x/config.py"
    text = path.read_text(encoding="utf-8")

    fields = (
        '    binance_live_base_url: str = "https://fapi.binance.com"\n'
        '    binance_testnet_base_url: str = "https://testnet.binancefuture.com"\n'
        "    binance_live_timeout_seconds: float = 10.0\n"
        "    binance_recv_window_ms: int = 5000\n"
        "    binance_maximum_time_drift_ms: int = 1000\n"
        "    binance_use_testnet: bool = True\n"
    )
    if "binance_live_base_url" not in text:
        marker = "    model_config = SettingsConfigDict("
        if marker not in text:
            raise RuntimeError("Config marker not found")
        text = text.replace(marker, fields + "\n" + marker, 1)
    path.write_text(text, encoding="utf-8")

    yaml = ROOT / "config/settings.yaml"
    ytext = yaml.read_text(encoding="utf-8")
    if "\nbinance_live:\n" not in ytext:
        ytext += (
            "\nbinance_live:\n"
            "  base_url: https://fapi.binance.com\n"
            "  testnet_url: https://testnet.binancefuture.com\n"
            "  timeout_seconds: 10.0\n"
            "  recv_window_ms: 5000\n"
            "  maximum_time_drift_ms: 1000\n"
            "  use_testnet: true\n"
        )
        yaml.write_text(ytext, encoding="utf-8")


def patch_version() -> None:
    pyproject = ROOT / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    text = re.sub(r'version = "[^"]+"', 'version = "0.21.0"', text, count=1)
    pyproject.write_text(text, encoding="utf-8")

    init = ROOT / "src/nexor_x/__init__.py"
    text = init.read_text(encoding="utf-8")
    text = re.sub(r'__version__\s*=\s*"[^"]+"', '__version__ = "0.21.0"', text)
    init.write_text(text, encoding="utf-8")


def main() -> None:
    patch_kernel()
    patch_api()
    patch_config()
    patch_version()
    print("Sprint 21 aplicada com sucesso.")


if __name__ == "__main__":
    main()
