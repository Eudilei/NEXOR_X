from __future__ import annotations

from typing import Any
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from nexor_x import __version__


class PaperCloseRequest(BaseModel):
    market_price: float = Field(gt=0)
    reason: str = Field(default="MANUAL", min_length=1, max_length=120)



class PositionManageRequest(BaseModel):
    market_price: float = Field(gt=0)

class MonteCarloRequest(BaseModel):
    symbol: str | None = Field(default=None, min_length=3, max_length=30)
    decision: str | None = Field(default=None, min_length=3, max_length=40)
    regime: str | None = Field(default=None, min_length=3, max_length=40)
    simulations: int | None = Field(default=None, ge=100, le=100000)
    horizon_trades: int | None = Field(default=None, ge=20, le=100000)
    block_size: int | None = Field(default=None, ge=1, le=10000)
    seed: int | None = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


def create_app(kernel: Any) -> FastAPI:
    app = FastAPI(title="NEXOR X", version=__version__)

    async def require_admin(x_nexor_admin_token: str | None = Header(default=None)) -> None:
        expected = kernel.settings.admin_api_token
        if not expected:
            raise HTTPException(
                status_code=503,
                detail="Controle administrativo desabilitado: configure NEXOR_ADMIN_API_TOKEN.",
            )
        if not x_nexor_admin_token or not secrets.compare_digest(x_nexor_admin_token, expected):
            raise HTTPException(status_code=401, detail="Token administrativo invalido.")

    @app.get("/", response_class=HTMLResponse)
    async def command_center() -> str:
        return COMMAND_CENTER

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "nexor-x", "version": __version__}

    @app.get("/api/status")
    async def status() -> dict[str, Any]:
        return await kernel.status()

    @app.get("/api/config")
    async def config() -> dict[str, Any]:
        return kernel.settings.public_dict()

    @app.get("/api/market/{symbol}")
    async def market(symbol: str) -> dict[str, Any]:
        try:
            return await kernel.market_state(symbol)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/quant/{symbol}")
    async def quant(symbol: str) -> dict[str, Any]:
        try:
            return await kernel.quant_assessment(symbol)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc


    @app.get("/api/probability/{symbol}")
    async def probability(symbol: str) -> dict[str, Any]:
        try:
            return await kernel.probability_assessment(symbol)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/market-diagnostics")
    async def market_diagnostics() -> dict[str, Any]:
        return kernel.binance.diagnostics()

    @app.get("/api/scanner/status")
    async def scanner_status() -> dict[str, Any]:
        return await kernel.scanner_status()

    @app.post("/api/scanner/run")
    async def scanner_run(_: None = Depends(require_admin)) -> dict[str, Any]:
        try:
            return await kernel.scanner_run()
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/laboratory/status")
    async def laboratory_status() -> dict[str, Any]:
        return await kernel.laboratory_status()

    @app.get("/api/edges/status")
    async def edge_status() -> dict[str, Any]:
        return await kernel.edge_status()

    @app.post("/api/edges/discover")
    async def discover_edges(_: None = Depends(require_admin)) -> dict[str, Any]:
        return await kernel.discover_edges()

    @app.get("/api/monte-carlo/status")
    async def monte_carlo_status() -> dict[str, Any]:
        return await kernel.monte_carlo_status()

    @app.post("/api/monte-carlo/run")
    async def monte_carlo_run(
        body: MonteCarloRequest, _: None = Depends(require_admin)
    ) -> dict[str, Any]:
        try:
            return await kernel.run_monte_carlo(
                symbol=body.symbol.upper() if body.symbol else None,
                decision=body.decision, regime=body.regime,
                simulations=body.simulations, horizon_trades=body.horizon_trades,
                block_size=body.block_size, seed=body.seed,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/portfolio/status")
    async def portfolio_status() -> dict[str, Any]:
        return await kernel.portfolio_status()

    @app.get("/api/trading/readiness/{symbol}")
    async def trading_readiness(symbol: str) -> dict[str, Any]:
        try:
            return await kernel.trading_readiness(symbol)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/api/paper/open/{symbol}")
    async def paper_open(symbol: str, _: None = Depends(require_admin)) -> dict[str, Any]:
        try:
            return await kernel.paper_open(symbol)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/api/paper/close/{position_id}")
    async def paper_close(position_id: int, body: PaperCloseRequest, _: None = Depends(require_admin)) -> dict[str, Any]:
        try:
            return await kernel.paper_close(position_id, body.market_price, body.reason)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


    @app.post("/api/positions/{position_id}/manage")
    async def manage_position(position_id: int, body: PositionManageRequest, _: None = Depends(require_admin)) -> dict[str, Any]:
        try:
            return await kernel.manage_position(position_id, body.market_price)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/positions/manage-all")
    async def manage_all_positions(_: None = Depends(require_admin)) -> dict[str, Any]:
        try:
            return await kernel.manage_all_positions()
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/api/ai/chat")
    async def chat(body: ChatRequest, _: None = Depends(require_admin)) -> dict[str, str]:
        system_status = await kernel.status()
        context = (
            "Voce e o copiloto do NEXOR X. Nao invente dados nem prometa lucro. "
            f"Modo: {kernel.settings.nexor_mode.value}. Estado: {system_status['state']}."
        )
        return {"answer": await kernel.ollama.chat(body.message, context)}

    @app.websocket("/ws/status")
    async def status_socket(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                await websocket.send_json(await kernel.status())
                await kernel.sleep(2.0)
        except WebSocketDisconnect:
            return

    return app


COMMAND_CENTER = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NEXOR X Command Center</title><style>
:root{--bg:#080c13;--panel:#111826;--panel2:#0d1420;--line:#24334b;--text:#eaf0fa;--muted:#91a2ba;--ok:#25d07f;--warn:#ffb547;--bad:#ff6474;--accent:#42a5ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px Segoe UI,Arial,sans-serif}.top{height:64px;display:flex;align-items:center;padding:0 24px;border-bottom:1px solid var(--line);background:#0c121d}.brand{font-size:21px;font-weight:800;letter-spacing:1.5px}.brand span{color:var(--accent)}.mode{margin-left:auto;padding:7px 12px;border:1px solid #24553f;border-radius:8px;color:var(--ok);background:#10231b}.layout{display:grid;grid-template-columns:220px 1fr;min-height:calc(100vh - 64px)}aside{border-right:1px solid var(--line);padding:18px 12px;background:#0b111b}.nav{padding:12px;border-radius:8px;color:var(--muted);margin:4px}.nav.active{background:#172236;color:var(--text)}main{padding:22px}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}.label{color:var(--muted);font-size:12px;text-transform:uppercase}.value{font-size:23px;font-weight:750;margin-top:8px}.small{font-size:13px;color:var(--muted);margin-top:8px}.wide{grid-column:span 2}.services{margin-top:14px;display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.service{background:var(--panel2);border:1px solid var(--line);padding:10px;border-radius:8px}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px;background:var(--bad)}.dot.ok{background:var(--ok)}.dot.warn{background:var(--warn)}input[type=password]{width:100%;background:#0b111c;color:var(--text);border:1px solid var(--line);border-radius:8px;padding:10px;margin-top:8px}textarea{width:100%;height:92px;background:#0b111c;color:var(--text);border:1px solid var(--line);border-radius:8px;padding:10px}button{margin-top:8px;background:var(--accent);border:0;color:#06101e;font-weight:700;padding:10px 16px;border-radius:8px;cursor:pointer}pre{white-space:pre-wrap;color:#cad7e9;min-height:82px}.foot{margin-top:16px;color:var(--muted);font-size:12px}@media(max-width:900px){.layout{grid-template-columns:1fr}aside{display:none}.grid{grid-template-columns:1fr}.wide{grid-column:span 1}.services{grid-template-columns:1fr}}
</style></head><body><header class="top"><div class="brand">NEXOR <span>X</span></div><div class="mode" id="mode">PAPER</div></header><div class="layout"><aside><div class="nav active">Visao Geral</div><div class="nav">Mercado</div><div class="nav">Estrategias</div><div class="nav">Carteira</div><div class="nav">Laboratorio</div><div class="nav">IA</div><div class="nav">Configuracoes</div><div class="nav">Sistema</div></aside><main><div class="grid"><section class="card"><div class="label">Sistema</div><div class="value" id="system">Carregando</div></section><section class="card"><div class="label">Servicos</div><div class="value" id="count">-</div></section><section class="card"><div class="label">BTCUSDT</div><div class="value" id="btc">-</div><div class="small" id="source">Aguardando mercado</div></section><section class="card"><div class="label">Regime</div><div class="value" id="regime">-</div><div class="small" id="marketReason">-</div></section><section class="card"><div class="label">Direcao</div><div class="value" id="direction">-</div></section><section class="card"><div class="label">Confianca do classificador</div><div class="value" id="confidence">-</div><div class="small">Nao representa probabilidade de lucro.</div></section><section class="card"><div class="label">Volatilidade</div><div class="value" id="volatility">-</div></section><section class="card"><div class="label">Dados</div><div class="value" id="freshness">-</div></section><section class="card"><div class="label">Quant Brain</div><div class="value" id="edgeDecision">-</div><div class="small" id="edgeNote">Aguardando evidencias</div></section><section class="card"><div class="label">Edge bruto</div><div class="value" id="rawEdge">-</div><div class="small">Sinal interno; nao e probabilidade de lucro.</div></section><section class="card"><div class="label">Calibracao</div><div class="value" id="calibration">-</div><div class="small" id="calibrationNote">Aguardando laboratorio</div></section><section class="card"><div class="label">Expected R</div><div class="value" id="expectedR">-</div><div class="small">Somente aparece com amostra historica suficiente.</div></section><section class="card wide"><div class="label">Scanner de mercado</div><div class="value" id="scannerState">Aguardando</div><div class="small" id="scannerSummary">Nenhuma varredura concluida.</div><div class="services" id="scannerCandidates"></div></section><section class="card wide"><div class="label">Saude dos modulos</div><div class="services" id="services"></div></section><section class="card wide"><div class="label">IA local (Ollama)</div><input id="adminToken" type="password" placeholder="Token administrativo"><textarea id="question" placeholder="Qual e o estado atual do sistema?"></textarea><button onclick="ask()">Perguntar</button><pre id="answer"></pre></section></div><div class="foot">NEXOR X 0.14.0 — Monte Carlo por blocos e diagnostico de robustez; LIVE continua bloqueado.</div></main></div><script>
function render(s){system.textContent=s.state;mode.textContent=s.mode;count.textContent=s.services.length;services.innerHTML=s.services.map(x=>`<div class="service"><span class="dot ${x.state==='HEALTHY'?'ok':x.state==='DEGRADED'?'warn':''}"></span><b>${x.name}</b><br><small>${x.state} — ${x.details||''}</small></div>`).join('')}
function connect(){const proto=location.protocol==='https:'?'wss':'ws';const ws=new WebSocket(`${proto}://${location.host}/ws/status`);ws.onmessage=e=>render(JSON.parse(e.data));ws.onclose=()=>setTimeout(connect,2000)}
async function market(){try{const r=await fetch('/api/market/BTCUSDT');const p=await r.json();if(!r.ok)throw new Error(p.detail||'Falha');btc.textContent='$ '+Number(p.snapshot.price).toLocaleString('pt-BR',{maximumFractionDigits:2});regime.textContent=p.regime;direction.textContent=p.direction;confidence.textContent=(p.confidence*100).toFixed(1)+'%';volatility.textContent=(p.volatility*100).toFixed(1)+'%';freshness.textContent=p.snapshot.stale?'CACHE ANTIGO':'ATUAL';source.textContent=p.snapshot.source;marketReason.textContent=p.rationale.join(' • ')}catch(e){btc.textContent='Indisponivel';regime.textContent='SEM DADOS';source.textContent=e.message}}
async function quant(){try{const r=await fetch('/api/quant/BTCUSDT');const q=await r.json();if(!r.ok)throw new Error(q.detail||'Falha');edgeDecision.textContent=q.decision;rawEdge.textContent=Number(q.raw_edge).toFixed(3);edgeNote.textContent=q.rationale.join(' • ');calibration.textContent=q.calibrated?'CALIBRADO':'NAO PRONTO';calibrationNote.textContent=q.calibration_samples+' observacoes';expectedR.textContent=q.expected_r===null?'-':Number(q.expected_r).toFixed(4)+' R'}catch(e){edgeDecision.textContent='INDISPONIVEL';edgeNote.textContent=e.message}}
async function scanner(){try{const r=await fetch('/api/scanner/status');const s=await r.json();if(!r.ok)throw new Error(s.detail||'Falha');scannerState.textContent=s.running?'VARRENDO':'PRONTO';if(!s.last_run){scannerSummary.textContent='Nenhuma varredura concluida.';scannerCandidates.innerHTML='';return}const x=s.last_run;scannerSummary.textContent=`${x.symbols_succeeded}/${x.symbols_requested} simbolos analisados • ${x.symbols_failed} falhas • sem execucao automatica`;scannerCandidates.innerHTML=x.candidates.map(c=>`<div class="service"><b>${c.symbol}</b><br><small>${c.decision} • edge ${Number(c.raw_edge).toFixed(3)} • rank ${Number(c.rank_score).toFixed(3)} • ${c.regime}</small></div>`).join('')}catch(e){scannerState.textContent='INDISPONIVEL';scannerSummary.textContent=e.message}}
async function ask(){answer.textContent='Processando...';const token=adminToken.value;try{const r=await fetch('/api/ai/chat',{method:'POST',headers:{'Content-Type':'application/json','X-NEXOR-ADMIN-TOKEN':token},body:JSON.stringify({message:question.value})}).then(r=>r.json());answer.textContent=r.answer||r.detail}catch(e){answer.textContent='Falha ao consultar a IA.'}}
connect();market();quant();scanner();setInterval(()=>{market();quant();scanner()},15000);
</script></body></html>"""
