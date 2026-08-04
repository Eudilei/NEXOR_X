from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"Marcador nao encontrado em {path}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_kernel() -> None:
    path = ROOT / "src/nexor_x/kernel.py"

    replace_once(
        path,
        "from nexor_x.position.service import PositionPolicy\n",
        "from nexor_x.position.service import PositionPolicy\n"
        "from nexor_x.strategy import StrategyOrchestrationService\n",
    )

    replace_once(
        path,
        "        self.scanner = MarketScannerService(\n",
        "        self.strategy_orchestration = StrategyOrchestrationService(self.database)\n"
        "        self.scanner = MarketScannerService(\n",
    )

    replace_once(
        path,
        "        await self.portfolio.ensure_account()\n"
        "        self._started = True\n",
        "        await self.portfolio.ensure_account()\n"
        "        await self.strategy_orchestration.start()\n"
        "        self._started = True\n",
    )

    replace_once(
        path,
        "    async def portfolio_status(self) -> dict[str, object]:\n",
        "    async def strategy_status(self) -> dict[str, object]:\n"
        "        return await self.strategy_orchestration.status()\n\n"
        "    async def strategy_rank(self, payload: dict[str, object]) -> dict[str, object]:\n"
        "        result = await self.strategy_orchestration.rank(\n"
        "            symbol=str(payload['symbol']),\n"
        "            regime=str(payload['regime']),\n"
        "            decision=str(payload['decision']),\n"
        "            metrics=list(payload.get('metrics') or []),\n"
        "            current_strategy_id=(\n"
        "                str(payload['current_strategy_id'])\n"
        "                if payload.get('current_strategy_id') else None\n"
        "            ),\n"
        "        )\n"
        "        await self.event_bus.publish(Event(\n"
        "            'strategy.selection',\n"
        "            {\n"
        "                'symbol': result['symbol'],\n"
        "                'selected_strategy_id': result['selected_strategy_id'],\n"
        "                'status': result['status'],\n"
        "                'execution_allowed': False,\n"
        "            },\n"
        "            'meta_strategy_orchestrator',\n"
        "        ))\n"
        "        return result\n\n"
        "    async def portfolio_status(self) -> dict[str, object]:\n",
    )

    replace_once(
        path,
        '        if event.topic.startswith(("system.", "market.", "quant.", "laboratory.", "risk.", "execution.", "position.")):\n',
        '        if event.topic.startswith(("system.", "market.", "quant.", "laboratory.", "risk.", "execution.", "position.", "strategy.")):\n',
    )


def patch_api() -> None:
    path = ROOT / "src/nexor_x/api/app.py"

    replace_once(
        path,
        "class ChatRequest(BaseModel):\n",
        "class StrategyMetricRequest(BaseModel):\n"
        "    strategy_id: str = Field(min_length=2, max_length=80)\n"
        "    sample_count: int = Field(ge=1, le=10000000)\n"
        "    profit_factor: float = Field(ge=0, le=1000)\n"
        "    expected_r: float = Field(ge=-100, le=100)\n"
        "    win_rate: float = Field(ge=0, le=1)\n"
        "    max_drawdown_r: float = Field(ge=0, le=100000)\n"
        "    brier_score: float | None = Field(default=None, ge=0, le=1)\n"
        "    walk_forward_pass_ratio: float | None = Field(default=None, ge=0, le=1)\n"
        "    monte_carlo_ruin_probability: float | None = Field(default=None, ge=0, le=1)\n\n"
        "class StrategyRankRequest(BaseModel):\n"
        "    symbol: str = Field(min_length=3, max_length=30)\n"
        "    regime: str = Field(min_length=3, max_length=40)\n"
        "    decision: str = Field(min_length=3, max_length=40)\n"
        "    current_strategy_id: str | None = Field(default=None, max_length=80)\n"
        "    metrics: list[StrategyMetricRequest] = Field(min_length=1, max_length=100)\n\n"
        "class ChatRequest(BaseModel):\n",
    )

    replace_once(
        path,
        "    @app.get(\"/api/portfolio/status\")\n",
        "    @app.get(\"/api/strategies/status\")\n"
        "    async def strategy_status() -> dict[str, Any]:\n"
        "        return await kernel.strategy_status()\n\n"
        "    @app.post(\"/api/strategies/rank\")\n"
        "    async def strategy_rank(\n"
        "        body: StrategyRankRequest, _: None = Depends(require_admin)\n"
        "    ) -> dict[str, Any]:\n"
        "        try:\n"
        "            return await kernel.strategy_rank(body.model_dump())\n"
        "        except (KeyError, TypeError, ValueError) as exc:\n"
        "            raise HTTPException(status_code=422, detail=str(exc)) from exc\n\n"
        "    @app.get(\"/api/portfolio/status\")\n",
    )


def patch_versions() -> None:
    pyproject = ROOT / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    text = text.replace('version = "0.16.0"', 'version = "0.18.0"')
    pyproject.write_text(text, encoding="utf-8")

    init = ROOT / "src/nexor_x/__init__.py"
    text = init.read_text(encoding="utf-8")
    import re
    text = re.sub(r'__version__\s*=\s*"[^"]+"', '__version__ = "0.18.0"', text)
    init.write_text(text, encoding="utf-8")


def patch_readme() -> None:
    path = ROOT / "README.md"
    text = path.read_text(encoding="utf-8")
    marker = "## Sprint 18 — Strategy Orchestrator integrado"
    if marker not in text:
        text += (
            "\n\n## Sprint 18 — Strategy Orchestrator integrado\n\n"
            "- registro persistente de estrategias;\n"
            "- ranking administrativo por contexto;\n"
            "- endpoints `/api/strategies/status` e `/api/strategies/rank`;\n"
            "- selecao permanece observacional e nao libera PAPER automatico ou LIVE.\n"
        )
        path.write_text(text, encoding="utf-8")


def main() -> None:
    patch_kernel()
    patch_api()
    patch_versions()
    patch_readme()
    print("Sprint 18 aplicada com sucesso.")


if __name__ == "__main__":
    main()
