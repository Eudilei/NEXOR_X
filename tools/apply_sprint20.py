from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def patch_kernel() -> None:
    path = ROOT / "src/nexor_x/kernel.py"
    text = path.read_text(encoding="utf-8")

    if "from nexor_x.certification import CertificationPolicy, CertificationService" not in text:
        marker = "from nexor_x.position.service import PositionPolicy\n"
        if marker not in text:
            raise RuntimeError("Import marker not found in kernel.py")
        text = text.replace(
            marker,
            marker + (
                "from nexor_x.certification import "
                "CertificationPolicy, CertificationService\n"
            ),
            1,
        )

    if "self.certification = CertificationService(" not in text:
        marker = "        self.scanner = MarketScannerService(\n"
        if marker not in text:
            raise RuntimeError("Scanner marker not found in kernel.py")
        block = (
            "        self.certification = CertificationService(\n"
            "            self.database,\n"
            "            CertificationPolicy(\n"
            "                minimum_paper_trades=settings.certification_minimum_paper_trades,\n"
            "                minimum_profit_factor=settings.certification_minimum_profit_factor,\n"
            "                minimum_expected_r=settings.certification_minimum_expected_r,\n"
            "                maximum_drawdown_pct=settings.certification_maximum_drawdown_pct,\n"
            "                minimum_walk_forward_pass_ratio=settings.certification_minimum_walk_forward_pass_ratio,\n"
            "                maximum_monte_carlo_ruin_probability=settings.certification_maximum_ruin_probability,\n"
            "                maximum_brier_score_oos=settings.certification_maximum_brier_score_oos,\n"
            "                maximum_calibration_ece_oos=settings.certification_maximum_ece_oos,\n"
            "                maximum_operational_incidents=0,\n"
            "                maximum_critical_test_failures=0,\n"
            "                minimum_days_in_paper=settings.certification_minimum_days_in_paper,\n"
            "                minimum_recent_profit_factor=settings.certification_minimum_recent_profit_factor,\n"
            "                minimum_recent_expected_r=settings.certification_minimum_recent_expected_r,\n"
            "            ),\n"
            "        )\n"
        )
        text = text.replace(marker, block + marker, 1)

    if "await self.certification.start()" not in text:
        marker = "        await self.portfolio.ensure_account()\n"
        if marker not in text:
            raise RuntimeError("Portfolio startup marker not found")
        text = text.replace(
            marker,
            marker + "        await self.certification.start()\n",
            1,
        )

    if "async def certification_status" not in text:
        marker = "    async def portfolio_status(self) -> dict[str, object]:\n"
        if marker not in text:
            raise RuntimeError("portfolio_status marker not found")
        methods = (
            "    async def certification_status(self) -> dict[str, object]:\n"
            "        return await self.certification.status()\n\n"
            "    async def certification_evaluate(\n"
            "        self, payload: dict[str, object]\n"
            "    ) -> dict[str, object]:\n"
            "        result = await self.certification.evaluate(payload)\n"
            "        await self.event_bus.publish(Event(\n"
            "            'certification.evaluated',\n"
            "            {\n"
            "                'status': result['status'],\n"
            "                'passed': result['passed'],\n"
            "                'live_execution_allowed': False,\n"
            "            },\n"
            "            'cqo_certification',\n"
            "        ))\n"
            "        return result\n\n"
        )
        text = text.replace(marker, methods + marker, 1)

    path.write_text(text, encoding="utf-8")


def patch_api() -> None:
    path = ROOT / "src/nexor_x/api/app.py"
    text = path.read_text(encoding="utf-8")

    if "class CertificationRequest(BaseModel):" not in text:
        marker = "class ChatRequest(BaseModel):\n"
        if marker not in text:
            raise RuntimeError("ChatRequest marker not found")
        model = (
            "class CertificationRequest(BaseModel):\n"
            "    paper_trades: int = Field(ge=0, le=100000000)\n"
            "    profit_factor: float = Field(ge=0, le=1000)\n"
            "    expected_r: float = Field(ge=-100, le=100)\n"
            "    maximum_drawdown_pct: float = Field(ge=0, le=100)\n"
            "    walk_forward_pass_ratio: float = Field(ge=0, le=1)\n"
            "    monte_carlo_ruin_probability: float = Field(ge=0, le=1)\n"
            "    brier_score_oos: float = Field(ge=0, le=1)\n"
            "    calibration_ece_oos: float = Field(ge=0, le=1)\n"
            "    operational_incidents: int = Field(ge=0, le=1000000)\n"
            "    critical_test_failures: int = Field(ge=0, le=1000000)\n"
            "    days_in_paper: int = Field(ge=0, le=100000)\n"
            "    recent_profit_factor: float = Field(ge=0, le=1000)\n"
            "    recent_expected_r: float = Field(ge=-100, le=100)\n"
            "    data_freshness_ok: bool\n"
            "    reconciliation_ok: bool\n"
            "    secrets_configured: bool\n"
            "    live_connector_tested: bool\n"
            "    manual_owner_approval: bool = False\n\n"
        )
        text = text.replace(marker, model + marker, 1)

    if '@app.get("/api/certification/status")' not in text:
        marker = '    @app.get("/api/portfolio/status")\n'
        if marker not in text:
            raise RuntimeError("portfolio endpoint marker not found")
        endpoints = (
            '    @app.get("/api/certification/status")\n'
            "    async def certification_status() -> dict[str, Any]:\n"
            "        return await kernel.certification_status()\n\n"
            '    @app.post("/api/certification/evaluate")\n'
            "    async def certification_evaluate(\n"
            "        body: CertificationRequest, _: None = Depends(require_admin)\n"
            "    ) -> dict[str, Any]:\n"
            "        try:\n"
            "            return await kernel.certification_evaluate(body.model_dump())\n"
            "        except (KeyError, TypeError, ValueError) as exc:\n"
            "            raise HTTPException(status_code=422, detail=str(exc)) from exc\n\n"
        )
        text = text.replace(marker, endpoints + marker, 1)

    path.write_text(text, encoding="utf-8")


def patch_config() -> None:
    path = ROOT / "src/nexor_x/config.py"
    text = path.read_text(encoding="utf-8")

    fields = (
        "    certification_minimum_paper_trades: int = 1000\n"
        "    certification_minimum_profit_factor: float = 1.40\n"
        "    certification_minimum_expected_r: float = 0.05\n"
        "    certification_maximum_drawdown_pct: float = 15.0\n"
        "    certification_minimum_walk_forward_pass_ratio: float = 0.70\n"
        "    certification_maximum_ruin_probability: float = 0.02\n"
        "    certification_maximum_brier_score_oos: float = 0.24\n"
        "    certification_maximum_ece_oos: float = 0.08\n"
        "    certification_minimum_days_in_paper: int = 30\n"
        "    certification_minimum_recent_profit_factor: float = 1.15\n"
        "    certification_minimum_recent_expected_r: float = 0.01\n"
    )
    if "certification_minimum_paper_trades" not in text:
        marker = "    model_config = SettingsConfigDict("
        if marker not in text:
            raise RuntimeError("Config insertion marker not found")
        text = text.replace(marker, fields + "\n" + marker, 1)
    path.write_text(text, encoding="utf-8")

    yaml = ROOT / "config/settings.yaml"
    ytext = yaml.read_text(encoding="utf-8")
    if "\ncertification:\n" not in ytext:
        ytext += (
            "\ncertification:\n"
            "  minimum_paper_trades: 1000\n"
            "  minimum_profit_factor: 1.40\n"
            "  minimum_expected_r: 0.05\n"
            "  maximum_drawdown_pct: 15.0\n"
            "  minimum_walk_forward_pass_ratio: 0.70\n"
            "  maximum_ruin_probability: 0.02\n"
            "  maximum_brier_score_oos: 0.24\n"
            "  maximum_ece_oos: 0.08\n"
            "  minimum_days_in_paper: 30\n"
            "  minimum_recent_profit_factor: 1.15\n"
            "  minimum_recent_expected_r: 0.01\n"
        )
        yaml.write_text(ytext, encoding="utf-8")


def patch_version() -> None:
    pyproject = ROOT / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    text = re.sub(r'version = "[^"]+"', 'version = "0.20.0"', text, count=1)
    pyproject.write_text(text, encoding="utf-8")

    init = ROOT / "src/nexor_x/__init__.py"
    text = init.read_text(encoding="utf-8")
    text = re.sub(r'__version__\s*=\s*"[^"]+"', '__version__ = "0.20.0"', text)
    init.write_text(text, encoding="utf-8")


def main() -> None:
    patch_kernel()
    patch_api()
    patch_config()
    patch_version()
    print("Sprint 20 aplicada com sucesso.")


if __name__ == "__main__":
    main()
