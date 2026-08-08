from __future__ import annotations

COMMAND_CENTER_V2 = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NEXOR X Command Center</title>
<style>
:root{
  --bg:#070b12;--panel:#0f1724;--panel2:#0b1320;--line:#22314a;
  --text:#eef4ff;--muted:#93a4bd;--ok:#30d889;--warn:#ffb84d;
  --bad:#ff6375;--accent:#4ca7ff;--violet:#9d7cff
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px Segoe UI,Arial,sans-serif}
.top{height:66px;display:flex;align-items:center;padding:0 22px;border-bottom:1px solid var(--line);background:#0b111b;position:sticky;top:0;z-index:4}
.brand{font-size:22px;font-weight:900;letter-spacing:1.5px}.brand span{color:var(--accent)}
.badges{margin-left:auto;display:flex;gap:8px;align-items:center}
.badge{padding:7px 10px;border:1px solid var(--line);border-radius:9px;color:var(--muted);background:#0d1522}
.badge.ok{color:var(--ok);border-color:#245d43}.badge.bad{color:var(--bad);border-color:#6c2d38}
.layout{display:grid;grid-template-columns:220px 1fr;min-height:calc(100vh - 66px)}
aside{border-right:1px solid var(--line);padding:18px 12px;background:#0a1019}
.nav{padding:12px;border-radius:8px;color:var(--muted);margin:4px}.nav.active{background:#172236;color:var(--text)}
main{padding:20px;max-width:1700px;width:100%;margin:auto}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px}
.card{background:linear-gradient(180deg,#111a29,#0d1521);border:1px solid var(--line);border-radius:12px;padding:15px;min-width:0}
.card.wide{grid-column:span 2}.card.full{grid-column:1/-1}
.label{color:var(--muted);font-size:11px;letter-spacing:.8px;text-transform:uppercase}
.value{font-size:22px;font-weight:800;margin-top:7px;overflow-wrap:anywhere}
.small{font-size:12px;color:var(--muted);margin-top:6px;line-height:1.45}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--bad);margin-right:7px}
.dot.ok{background:var(--ok)}.dot.warn{background:var(--warn)}
.stack{display:grid;gap:8px;margin-top:10px}
.item{background:var(--panel2);border:1px solid var(--line);padding:10px;border-radius:8px}
.meter{height:7px;background:#09101a;border-radius:10px;overflow:hidden;margin-top:8px}.meter>span{display:block;height:100%;background:var(--accent)}
input,textarea{width:100%;background:#09111c;color:var(--text);border:1px solid var(--line);border-radius:8px;padding:10px}
textarea{height:90px;resize:vertical}
button{background:var(--accent);border:0;color:#06101e;font-weight:800;padding:10px 15px;border-radius:8px;cursor:pointer}
button.secondary{background:#18263b;color:var(--text);border:1px solid var(--line)}
pre{white-space:pre-wrap;color:#d4e0f2;min-height:70px;margin:8px 0 0}
.error{color:var(--bad)}.oktxt{color:var(--ok)}.warntext{color:var(--warn)}
.foot{margin:18px 0 4px;color:var(--muted);font-size:12px}
@media(max-width:1100px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:760px){.layout{grid-template-columns:1fr}aside{display:none}.grid{grid-template-columns:1fr}.card.wide,.card.full{grid-column:span 1}.top{padding:0 12px}}
</style>
</head>
<body>
<header class="top">
  <div class="brand">NEXOR <span>X</span></div>
  <div class="badges">
    <div class="badge" id="versionBadge">v-</div>
    <div class="badge" id="modeBadge">PAPER</div>
    <div class="badge" id="liveBadge">LIVE BLOQUEADO</div>
  </div>
</header>
<div class="layout">
<aside>
  <div class="nav active">Visão Geral</div><div class="nav">Mercado</div>
  <div class="nav">Estratégias</div><div class="nav">Carteira</div>
  <div class="nav">Laboratório</div><div class="nav">Execução</div>
  <div class="nav">IA</div><div class="nav">Sistema</div>
</aside>
<main>
<div class="grid">
  <section class="card"><div class="label">Sistema</div><div class="value" id="systemState">-</div><div class="small" id="serviceSummary">-</div></section>
  <section class="card"><div class="label">Supervisor</div><div class="value" id="supervisorState">-</div><div class="small" id="supervisorBlockers">Sem avaliação.</div></section>
  <section class="card"><div class="label">Recovery Guard</div><div class="value" id="recoveryState">-</div><div class="small" id="recoveryNote">-</div></section>
  <section class="card"><div class="label">Certificação CQO</div><div class="value" id="certState">-</div><div class="small" id="certNote">LIVE continua bloqueado.</div></section>

  <section class="card"><div class="label">BTCUSDT</div><div class="value" id="btcPrice">-</div><div class="small" id="marketSource">-</div></section>
  <section class="card"><div class="label">Regime</div><div class="value" id="regime">-</div><div class="small" id="direction">-</div></section>
  <section class="card"><div class="label">Quant Brain</div><div class="value" id="quantDecision">-</div><div class="small" id="quantEdge">-</div></section>
  <section class="card"><div class="label">Probability</div><div class="value" id="probability">-</div><div class="small" id="probabilityNote">-</div></section>

  <section class="card wide"><div class="label">Portfólio PAPER</div><div class="row" style="margin-top:10px">
    <div><div class="small">Equity</div><div class="value" id="equity">-</div></div>
    <div><div class="small">Drawdown</div><div class="value" id="drawdown">-</div></div>
    <div><div class="small">Posições</div><div class="value" id="openPositions">-</div></div>
  </div></section>

  <section class="card wide"><div class="label">Scanner</div><div class="value" id="scannerState">-</div><div class="small" id="scannerSummary">-</div><div class="stack" id="scannerCandidates"></div></section>

  <section class="card wide"><div class="label">Estratégias</div><div class="value" id="strategyState">-</div><div class="small" id="strategyNote">-</div></section>
  <section class="card wide"><div class="label">Alocação</div><div class="value" id="allocationState">-</div><div class="small" id="allocationNote">-</div></section>

  <section class="card full"><div class="label">Saúde dos módulos</div><div class="stack" id="services"></div></section>

  <section class="card full">
    <div class="label">IA local — Ollama</div>
    <div class="small">O token fica apenas nesta página e não é salvo pelo navegador.</div>
    <input id="adminToken" type="password" placeholder="X-NEXOR-ADMIN-TOKEN" style="margin-top:9px">
    <textarea id="question" placeholder="Explique o estado atual do NEXOR X." style="margin-top:8px"></textarea>
    <div class="row"><button onclick="ask()">Perguntar</button><button class="secondary" onclick="refreshAll()">Atualizar painel</button></div>
    <pre id="answer"></pre>
  </section>
</div>
<div class="foot">NEXOR X Command Center v2 — dados operacionais e quantitativos. Nenhuma informação exibida representa garantia de lucro.</div>
</main></div>
<script>
const $=id=>document.getElementById(id);
async function getJSON(url, options={}) {
  const r=await fetch(url,options);
  const p=await r.json().catch(()=>({detail:`HTTP ${r.status}`}));
  if(!r.ok) throw new Error(p.detail||`HTTP ${r.status}`);
  return p;
}
function adminHeaders(){const t=$('adminToken').value.trim();return t?{'X-NEXOR-ADMIN-TOKEN':t}:{}}
function fmtNumber(v,d=2){if(v===null||v===undefined||Number.isNaN(Number(v)))return '-';return Number(v).toLocaleString('pt-BR',{maximumFractionDigits:d})}
function setText(id,text,cls=''){const el=$(id);el.textContent=text;el.className=(el.className.split(' ')[0]||'')+(cls?' '+cls:'')}
async function publicState(){
  try{
    const [s,m,q,p,portfolio,scanner,strategies,allocation]=await Promise.all([
      getJSON('/api/status'),
      getJSON('/api/market/BTCUSDT').catch(()=>null),
      getJSON('/api/quant/BTCUSDT').catch(()=>null),
      getJSON('/api/probability/BTCUSDT').catch(()=>null),
      getJSON('/api/portfolio/status').catch(()=>null),
      getJSON('/api/scanner/status').catch(()=>null),
      getJSON('/api/strategies/status').catch(()=>null),
      getJSON('/api/allocation/status').catch(()=>null)
    ]);
    $('systemState').textContent=s.state;$('modeBadge').textContent=s.mode;$('versionBadge').textContent='v'+(s.version||'-');
    $('liveBadge').textContent=s.live_certified?'LIVE CERTIFICADO':'LIVE BLOQUEADO';$('liveBadge').className='badge '+(s.live_certified?'ok':'bad');
    $('serviceSummary').textContent=`${s.services.length} serviços • fila ${s.event_queue}`;
    $('services').innerHTML=s.services.map(x=>`<div class="item"><span class="dot ${x.state==='HEALTHY'?'ok':x.state==='DEGRADED'?'warn':''}"></span><b>${x.name}</b> <span class="small">${x.state} ${x.details?'— '+x.details:''}</span></div>`).join('');
    if(m){$('btcPrice').textContent='$ '+fmtNumber(m.snapshot?.price,2);$('marketSource').textContent=(m.snapshot?.source||'-')+(m.snapshot?.stale?' • STALE':'');$('regime').textContent=m.regime||'-';$('direction').textContent=m.direction||'-'}
    if(q){$('quantDecision').textContent=q.decision||'-';$('quantEdge').textContent=`edge bruto ${fmtNumber(q.raw_edge,4)} • ${q.calibrated?'calibrado':'não calibrado'}`}
    if(p){$('probability').textContent=p.ready&&p.calibrated_probability!==null?fmtNumber(Number(p.calibrated_probability)*100,1)+'%':'NÃO PRONTO';$('probabilityNote').textContent=`${p.method||'-'} • ${p.sample_count||0} amostras`}
    if(portfolio){const a=portfolio.account||portfolio;$('equity').textContent=fmtNumber(a.equity,2);$('drawdown').textContent=fmtNumber(a.drawdown_pct,2)+'%';$('openPositions').textContent=String((portfolio.open_positions||[]).length)}
    if(scanner){$('scannerState').textContent=scanner.running?'VARRENDO':'PRONTO';const x=scanner.last_run;if(x){$('scannerSummary').textContent=`${x.symbols_succeeded}/${x.symbols_requested} analisados • ${x.symbols_failed} falhas`;$('scannerCandidates').innerHTML=(x.candidates||[]).slice(0,6).map(c=>`<div class="item"><b>${c.symbol}</b> <span class="small">${c.decision} • ${c.regime} • edge ${fmtNumber(c.raw_edge,3)}</span></div>`).join('')}}
    if(strategies){$('strategyState').textContent=strategies.latest_selection?.selected_strategy_id||'SEM SELEÇÃO';$('strategyNote').textContent=`${strategies.strategy_count||0} registradas • execução bloqueada`}
    if(allocation){$('allocationState').textContent=allocation.latest_plan?.status||'SEM PLANO';$('allocationNote').textContent=allocation.latest_plan?`risco ${fmtNumber(allocation.latest_plan.total_risk_budget_pct,2)}% • peso ${fmtNumber(allocation.latest_plan.total_weight,3)}`:'Nenhum plano persistido.'}
  }catch(e){$('systemState').textContent='INDISPONÍVEL';$('serviceSummary').textContent=e.message}
}
async function privateState(){
  const h=adminHeaders();if(!Object.keys(h).length){$('supervisorState').textContent='TOKEN NECESSÁRIO';$('recoveryState').textContent='TOKEN NECESSÁRIO';$('certState').textContent='TOKEN NECESSÁRIO';return}
  try{const r=await getJSON('/api/recovery/status',{headers:h});const x=r.latest_report;$('recoveryState').textContent=x?(x.recovery_ok?'OK':'LOCKED'):'SEM RECONCILIAÇÃO';$('recoveryNote').textContent=x?`${(x.issues||[]).length} divergências`:'Execute a reconciliação antes de TESTNET.'}catch(e){$('recoveryState').textContent='INDISPONÍVEL';$('recoveryNote').textContent=e.message}
  try{const s=await getJSON('/api/supervisor/status',{headers:h});const x=s.latest;$('supervisorState').textContent=x?.status||'SEM AVALIAÇÃO';$('supervisorBlockers').textContent=x?.blockers?.length?x.blockers.join(' • '):'Nenhum blocker persistido.'}catch(e){$('supervisorState').textContent='INDISPONÍVEL';$('supervisorBlockers').textContent=e.message}
  try{const c=await getJSON('/api/certification/status',{headers:h});const x=c.latest_certification;$('certState').textContent=x?.status||'SEM CERTIFICAÇÃO';$('certNote').textContent=x?.blockers?.length?x.blockers.join(' • '):'LIVE continua bloqueado.'}catch(e){$('certState').textContent='INDISPONÍVEL';$('certNote').textContent=e.message}
}
async function ask(){
  const token=$('adminToken').value.trim(),message=$('question').value.trim();if(!token||!message)return;
  $('answer').textContent='Consultando...';
  try{const p=await getJSON('/api/ai/chat',{method:'POST',headers:{'Content-Type':'application/json','X-NEXOR-ADMIN-TOKEN':token},body:JSON.stringify({message})});$('answer').textContent=p.answer}catch(e){$('answer').textContent=e.message}
}
async function refreshAll(){await publicState();await privateState()}
$('adminToken').addEventListener('change',privateState);
refreshAll();setInterval(publicState,15000);
const proto=location.protocol==='https:'?'wss':'ws';let ws;
function connect(){ws=new WebSocket(`${proto}://${location.host}/ws/status`);ws.onmessage=()=>publicState();ws.onclose=()=>setTimeout(connect,2500)}
connect();
</script>
</body></html>"""
