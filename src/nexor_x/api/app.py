from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from nexor_x import __version__


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


def create_app(kernel: Any) -> FastAPI:
    app = FastAPI(title="NEXOR X", version=__version__)

    @app.get("/", response_class=HTMLResponse)
    async def command_center() -> str:
        return COMMAND_CENTER

    @app.get("/api/status")
    async def status() -> dict[str, Any]:
        return await kernel.status()

    @app.get("/api/config")
    async def config() -> dict[str, Any]:
        return kernel.settings.public_dict()

    @app.get("/api/market/{symbol}")
    async def market(symbol: str) -> dict[str, Any]:
        normalized = symbol.upper().replace("/", "")
        if not normalized.endswith("USDT") or not normalized.isalnum():
            raise HTTPException(status_code=422, detail="Simbolo invalido.")
        try:
            price = await kernel.binance.ticker_price(normalized)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return {"symbol": normalized, "price": price, "source": "Binance Futures real data"}

    @app.post("/api/ai/chat")
    async def chat(body: ChatRequest) -> dict[str, str]:
        system_status = await kernel.status()
        context = (
            "Voce e o copiloto do NEXOR X. Nao invente dados. "
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
:root{--bg:#080c13;--panel:#111826;--panel2:#0d1420;--line:#24334b;--text:#eaf0fa;--muted:#91a2ba;--ok:#25d07f;--bad:#ff6474;--accent:#42a5ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px Segoe UI,Arial,sans-serif}.top{height:64px;display:flex;align-items:center;padding:0 24px;border-bottom:1px solid var(--line);background:#0c121d}.brand{font-size:21px;font-weight:800;letter-spacing:1.5px}.brand span{color:var(--accent)}.mode{margin-left:auto;padding:7px 12px;border:1px solid #24553f;border-radius:8px;color:var(--ok);background:#10231b}.layout{display:grid;grid-template-columns:220px 1fr;min-height:calc(100vh - 64px)}aside{border-right:1px solid var(--line);padding:18px 12px;background:#0b111b}.nav{padding:12px;border-radius:8px;color:var(--muted);margin:4px}.nav.active{background:#172236;color:var(--text)}main{padding:22px}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}.label{color:var(--muted);font-size:12px;text-transform:uppercase}.value{font-size:23px;font-weight:750;margin-top:8px}.wide{grid-column:span 2}.services{margin-top:14px;display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.service{background:var(--panel2);border:1px solid var(--line);padding:10px;border-radius:8px}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px;background:var(--bad)}.dot.ok{background:var(--ok)}textarea{width:100%;height:92px;background:#0b111c;color:var(--text);border:1px solid var(--line);border-radius:8px;padding:10px}button{margin-top:8px;background:var(--accent);border:0;color:#06101e;font-weight:700;padding:10px 16px;border-radius:8px;cursor:pointer}pre{white-space:pre-wrap;color:#cad7e9;min-height:82px}.foot{margin-top:16px;color:var(--muted);font-size:12px}@media(max-width:900px){.layout{grid-template-columns:1fr}aside{display:none}.grid{grid-template-columns:1fr}.wide{grid-column:span 1}.services{grid-template-columns:1fr}}
</style></head><body><header class="top"><div class="brand">NEXOR <span>X</span></div><div class="mode" id="mode">PAPER</div></header><div class="layout"><aside><div class="nav active">Visao Geral</div><div class="nav">Mercado</div><div class="nav">Estrategias</div><div class="nav">Carteira</div><div class="nav">Laboratorio</div><div class="nav">IA</div><div class="nav">Configuracoes</div><div class="nav">Sistema</div></aside><main><div class="grid"><section class="card"><div class="label">Sistema</div><div class="value" id="system">Carregando</div></section><section class="card"><div class="label">Servicos</div><div class="value" id="count">-</div></section><section class="card"><div class="label">BTCUSDT real</div><div class="value" id="btc">-</div></section><section class="card"><div class="label">Trading</div><div class="value" id="trading">PAPER</div></section><section class="card wide"><div class="label">Saude dos modulos</div><div class="services" id="services"></div></section><section class="card wide"><div class="label">IA local (Ollama)</div><textarea id="question" placeholder="Qual e o estado atual do sistema?"></textarea><button onclick="ask()">Perguntar</button><pre id="answer"></pre></section></div><div class="foot">NEXOR X 0.2.0 — dados reais, execucao ainda bloqueada nesta fase.</div></main></div><script>
function render(s){system.textContent=s.state;mode.textContent=s.mode;trading.textContent=s.mode;count.textContent=s.services.length;services.innerHTML=s.services.map(x=>`<div class="service"><span class="dot ${x.state==='HEALTHY'?'ok':''}"></span><b>${x.name}</b><br><small>${x.state} — ${x.details||''}</small></div>`).join('')}
function connect(){const proto=location.protocol==='https:'?'wss':'ws';const ws=new WebSocket(`${proto}://${location.host}/ws/status`);ws.onmessage=e=>render(JSON.parse(e.data));ws.onclose=()=>setTimeout(connect,2000)}
async function price(){try{const p=await fetch('/api/market/BTCUSDT').then(r=>r.json());btc.textContent='$ '+Number(p.price).toLocaleString('pt-BR',{maximumFractionDigits:2})}catch(e){btc.textContent='Indisponivel'}}
async function ask(){answer.textContent='Processando...';try{const r=await fetch('/api/ai/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:question.value})}).then(r=>r.json());answer.textContent=r.answer||r.detail}catch(e){answer.textContent='Falha ao consultar a IA.'}}
connect();price();setInterval(price,15000);
</script></body></html>"""
