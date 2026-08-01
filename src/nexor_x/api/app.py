from __future__ import annotations
from typing import Any
from fastapi import FastAPI, HTTPException
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

    @app.get("/api/market/{symbol}")
    async def market(symbol: str) -> dict[str, Any]:
        normalized = symbol.upper().replace("/", "")
        try:
            price = await kernel.binance.ticker_price(normalized)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return {"symbol": normalized, "price": price, "source": "Binance Futures real data"}

    @app.post("/api/ai/chat")
    async def chat(body: ChatRequest) -> dict[str, str]:
        context = f"Operating mode: {kernel.settings.nexor_mode.value}."
        return {"answer": await kernel.ollama.chat(body.message, context)}

    return app

COMMAND_CENTER = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NEXOR X Command Center</title><style>
:root{--bg:#090d14;--panel:#111827;--line:#24324a;--text:#e8eef9;--muted:#91a0b8;--ok:#27d17f;--warn:#f0b429;--accent:#41a5ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px Segoe UI,Arial,sans-serif}
.top{height:64px;display:flex;align-items:center;padding:0 24px;border-bottom:1px solid var(--line);background:#0d1320}
.brand{font-size:20px;font-weight:800;letter-spacing:1.5px}.brand span{color:var(--accent)}
.mode{margin-left:auto;padding:7px 12px;border:1px solid #24553f;border-radius:8px;color:var(--ok);background:#10231b}
.layout{display:grid;grid-template-columns:220px 1fr;min-height:calc(100vh - 64px)}
aside{border-right:1px solid var(--line);padding:18px 12px;background:#0c121d}
.nav{padding:12px;border-radius:8px;color:var(--muted);margin:4px}.nav.active{background:#172033;color:var(--text)}
main{padding:22px}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}
.label{color:var(--muted);font-size:12px;text-transform:uppercase}.value{font-size:24px;font-weight:750;margin-top:8px}
.wide{grid-column:span 2}.services{margin-top:14px;display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.service{background:#0d1421;border:1px solid var(--line);padding:10px;border-radius:8px}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px;background:var(--warn)}.dot.ok{background:var(--ok)}
textarea{width:100%;height:90px;background:#0b111c;color:var(--text);border:1px solid var(--line);border-radius:8px;padding:10px}
button{margin-top:8px;background:var(--accent);border:0;color:#06101e;font-weight:700;padding:10px 16px;border-radius:8px}
pre{white-space:pre-wrap;color:#c9d5e8;min-height:80px}@media(max-width:900px){.layout{grid-template-columns:1fr}aside{display:none}.grid{grid-template-columns:1fr}.wide{grid-column:span 1}}
</style></head><body><header class="top"><div class="brand">NEXOR <span>X</span></div><div class="mode" id="mode">PAPER</div></header>
<div class="layout"><aside><div class="nav active">Visão Geral</div><div class="nav">Mercado</div><div class="nav">Estratégias</div><div class="nav">Carteira</div><div class="nav">Laboratório</div><div class="nav">IA</div><div class="nav">Configurações</div><div class="nav">Sistema</div></aside>
<main><div class="grid"><section class="card"><div class="label">Sistema</div><div class="value" id="system">Carregando</div></section>
<section class="card"><div class="label">Serviços</div><div class="value" id="count">-</div></section>
<section class="card"><div class="label">BTCUSDT real</div><div class="value" id="btc">-</div></section>
<section class="card"><div class="label">Trading</div><div class="value">PAPER</div></section>
<section class="card wide"><div class="label">Saúde dos módulos</div><div class="services" id="services"></div></section>
<section class="card wide"><div class="label">IA local (Ollama)</div><textarea id="question" placeholder="Qual é o estado atual do sistema?"></textarea><button onclick="ask()">Perguntar</button><pre id="answer"></pre></section>
</div></main></div><script>
async function load(){try{const s=await fetch('/api/status').then(r=>r.json());system.textContent=s.state;mode.textContent=s.mode;count.textContent=s.services.length;services.innerHTML=s.services.map(x=>`<div class="service"><span class="dot ${x.state==='HEALTHY'?'ok':''}"></span><b>${x.name}</b><br><small>${x.state} — ${x.details||''}</small></div>`).join('')}catch(e){system.textContent='OFFLINE'}}
async function price(){try{const p=await fetch('/api/market/BTCUSDT').then(r=>r.json());btc.textContent='$ '+Number(p.price).toLocaleString('pt-BR',{maximumFractionDigits:2})}catch(e){btc.textContent='Indisponível'}}
async function ask(){answer.textContent='Processando...';try{const r=await fetch('/api/ai/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:question.value})}).then(r=>r.json());answer.textContent=r.answer||r.detail}catch(e){answer.textContent='Falha ao consultar a IA.'}}
load();price();setInterval(load,5000);setInterval(price,15000);
</script></body></html>"""
