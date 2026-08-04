from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"Marcador nao encontrado em {path}: {old[:100]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_kernel() -> None:
    path = ROOT / "src/nexor_x/kernel.py"
    text = path.read_text(encoding="utf-8")

    if "from nexor_x.allocation import AllocationService, AllocationPolicy" not in text:
        marker = "from nexor_x.position.service import PositionPolicy\n"
        if marker not in text:
            raise RuntimeError("Import marker not found in kernel.py")
        text = text.replace(
            marker,
            marker + "from nexor_x.allocation import AllocationService, AllocationPolicy\n",
            1,
        )

    if "self.allocation = AllocationService(" not in text:
        marker = "        self.scanner = MarketScannerService(\n"
        if marker not in text:
            raise RuntimeError("Scanner marker not found in kernel.py")
        block = (
            "        self.allocation = AllocationService(\n"
            "            self.database,\n"
            "            AllocationPolicy(\n"
            "                maximum_candidates=settings.allocation_maximum_candidates,\n"
            "                maximum_weight_per_candidate=settings.allocation_maximum_weight_per_candidate,\n"
            "                maximum_weight_per_correlation_group=settings.allocation_maximum_weight_per_correlation_group,\n"
            "                minimum_score=settings.allocation_minimum_score,\n"
            "                minimum_expected_r=settings.minimum_expected_r,\n"
            "                minimum_profit_factor=settings.minimum_profit_factor,\n"
            "                minimum_walk_forward_pass_ratio=settings.walk_forward_minimum_pass_ratio,\n"
            "                maximum_ruin_probability=settings.allocation_maximum_ruin_probability,\n"
            "                maximum_candidate_drawdown_r=settings.allocation_maximum_candidate_drawdown_r,\n"
            "                maximum_portfolio_risk_pct=settings.risk_per_trade_pct,\n"
            "                recovery_drawdown_trigger_pct=settings.allocation_recovery_drawdown_trigger_pct,\n"
            "                hard_stop_drawdown_pct=settings.hard_stop_drawdown_pct,\n"
            "                recovery_risk_multiplier=settings.allocation_recovery_risk_multiplier,\n"
            "            ),\n"
            "        )\n"
        )
        text = text.replace(marker, block + marker, 1)

    if "await self.allocation.start()" not in text:
        marker = "        await self.portfolio.ensure_account()\n"
        if marker not in text:
            raise RuntimeError("Portfolio startup marker not found")
        text = text.replace(
            marker,
            marker + "        await self.allocation.start()\n",
            1,
        )

    if "async def allocation_status" not in text:
        marker = "    async def portfolio_status(self) -> dict[str, object]:\n"
        if marker not in text:
            raise RuntimeError("portfolio_status marker not found")
        methods = (
            "    async def allocation_status(self) -> dict[str, object]:\n"
            "        return await self.allocation.status()\n\n"
            "    async def allocation_plan(self, payload: dict[str, object]) -> dict[str, object]:\n"
            "        result = await self.allocation.plan(\n"
            "            portfolio_drawdown_pct=float(payload['portfolio_drawdown_pct']),\n"
            "            candidates=list(payload.get('candidates') or []),\n"
            "        )\n"
            "        await self.event_bus.publish(Event(\n"
            "            'portfolio.allocation_plan',\n"
            "            {\n"
            "                'status': result['status'],\n"
            "                'total_weight': result['total_weight'],\n"
            "                'total_risk_budget_pct': result['total_risk_budget_pct'],\n"
            "                'execution_allowed': False,\n"
            "            },\n"
            "            'adaptive_portfolio_allocator',\n"
            "        ))\n"
            "        return result\n\n"
        )
        text = text.replace(marker, methods + marker, 1)

    path.write_text(text, encoding="utf-8")


def patch_api() -> None:
    path = ROOT / "src/nexor_x/api/app.py"
    text = path.read_text(encoding="utf-8")

    if "class AllocationCandidateRequest(BaseModel):" not in text:
        marker = "class ChatRequest(BaseModel):\n"
        if marker not in text:
            raise RuntimeError("ChatRequest marker not found")
        models = (
            "class AllocationCandidateRequest(BaseModel):\n"
            "    strategy_id: str = Field(min_length=2, max_length=80)\n"
            "    symbol: str = Field(min_length=3, max_length=30)\n"
            "    direction: str = Field(min_length=3, max_length=40)\n"
            "    score: float = Field(ge=-100, le=100)\n"
            "    expected_r: float = Field(ge=-100, le=100)\n"
            "    profit_factor: float = Field(ge=0, le=1000)\n"
            "    walk_forward_pass_ratio: float = Field(ge=0, le=1)\n"
            "    monte_carlo_ruin_probability: float = Field(ge=0, le=1)\n"
            "    max_drawdown_r: float = Field(ge=0, le=100000)\n"
            "    current_drawdown_pct: float = Field(default=0, ge=0, le=100)\n"
            "    correlation_group: str = Field(default='DEFAULT', max_length=80)\n\n"
            "class AllocationPlanRequest(BaseModel):\n"
            "    portfolio_drawdown_pct: float = Field(ge=0, le=100)\n"
            "    candidates: list[AllocationCandidateRequest] = Field(min_length=1, max_length=100)\n\n"
        )
        text = text.replace(marker, models + marker, 1)

    if '@app.get("/api/allocation/status")' not in text:
        marker = '    @app.get("/api/portfolio/status")\n'
        if marker not in text:
            raise RuntimeError("portfolio endpoint marker not found")
        endpoints = (
            '    @app.get("/api/allocation/status")\n'
            "    async def allocation_status() -> dict[str, Any]:\n"
            "        return await kernel.allocation_status()\n\n"
            '    @app.post("/api/allocation/plan")\n'
            "    async def allocation_plan(\n"
            "        body: AllocationPlanRequest, _: None = Depends(require_admin)\n"
            "    ) -> dict[str, Any]:\n"
            "        try:\n"
            "            return await kernel.allocation_plan(body.model_dump())\n"
            "        except (KeyError, TypeError, ValueError) as exc:\n"
            "            raise HTTPException(status_code=422, detail=str(exc)) from exc\n\n"
        )
        text = text.replace(marker, endpoints + marker, 1)

    path.write_text(text, encoding="utf-8")


def patch_config() -> None:
    path = ROOT / "src/nexor_x/config.py"
    text = path.read_text(encoding="utf-8")

    fields = (
        "    allocation_maximum_candidates: int = 5\n"
        "    allocation_maximum_weight_per_candidate: float = 0.35\n"
        "    allocation_maximum_weight_per_correlation_group: float = 0.55\n"
        "    allocation_minimum_score: float = 0.20\n"
        "    allocation_maximum_ruin_probability: float = 0.05\n"
        "    allocation_maximum_candidate_drawdown_r: float = 8.0\n"
        "    allocation_recovery_drawdown_trigger_pct: float = 10.0\n"
        "    allocation_recovery_risk_multiplier: float = 0.35\n"
    )
    if "allocation_maximum_candidates" not in text:
        marker = "    counterfactual_edge_thresholds: str = \"0.10,0.20,0.30,0.40,0.50\"\n"
        if marker not in text:
            # fallback before model_config
            marker = "    model_config = SettingsConfigDict("
            if marker not in text:
                raise RuntimeError("Config insertion marker not found")
            text = text.replace(marker, fields + "\n" + marker, 1)
        else:
            text = text.replace(marker, marker + fields, 1)
    path.write_text(text, encoding="utf-8")

    yaml = ROOT / "config/settings.yaml"
    ytext = yaml.read_text(encoding="utf-8")
    if "\nallocation:\n" not in ytext:
        ytext += (
            "\nallocation:\n"
            "  maximum_candidates: 5\n"
            "  maximum_weight_per_candidate: 0.35\n"
            "  maximum_weight_per_correlation_group: 0.55\n"
            "  minimum_score: 0.20\n"
            "  maximum_ruin_probability: 0.05\n"
            "  maximum_candidate_drawdown_r: 8.0\n"
            "  recovery_drawdown_trigger_pct: 10.0\n"
            "  recovery_risk_multiplier: 0.35\n"
        )
        yaml.write_text(ytext, encoding="utf-8")


def patch_version() -> None:
    pyproject = ROOT / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    text = re.sub(r'version = "[^"]+"', 'version = "0.19.0"', text, count=1)
    pyproject.write_text(text, encoding="utf-8")

    init = ROOT / "src/nexor_x/__init__.py"
    text = init.read_text(encoding="utf-8")
    text = re.sub(r'__version__\s*=\s*"[^"]+"', '__version__ = "0.19.0"', text)
    init.write_text(text, encoding="utf-8")


def main() -> None:
    patch_kernel()
    patch_api()
    patch_config()
    patch_version()
    print("Sprint 19 aplicada com sucesso.")


if __name__ == "__main__":
    main()
