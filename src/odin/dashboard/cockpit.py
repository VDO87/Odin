"""Local read-only HTML cockpit for the ODIN dashboard."""

from __future__ import annotations


def cockpit_html() -> str:
    """Return a dependency-free local dashboard shell with no write controls."""
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ODIN Cockpit</title><style>
:root{color-scheme:dark;--bg:#0b1020;--panel:#151d32;--line:#293553;--ok:#40d49a;--warn:#ffc857;--bad:#ff6b6b;--text:#e9efff;--muted:#aab8d6}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px system-ui,sans-serif}header{padding:20px 28px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:12px;align-items:center}h1{margin:0;font-size:22px}.tag{border:1px solid var(--line);border-radius:999px;padding:5px 10px;color:var(--muted)}main{padding:24px;max-width:1400px;margin:auto}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}.label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.08em}.value{font-size:22px;margin-top:8px;font-weight:650}.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}pre{white-space:pre-wrap;word-break:break-word;max-height:370px;overflow:auto;margin:10px 0 0;font:12px ui-monospace,monospace}button{background:#24375f;border:1px solid #3a548a;color:var(--text);border-radius:7px;padding:8px 12px;cursor:pointer}section{margin-top:22px}small{color:var(--muted)}</style></head>
<body><header><div><h1>ODIN Cockpit</h1><small>Local, read-only operational observability</small></div><div><span class="tag" id="updated">loading</span> <button onclick="loadAll()">Refresh</button></div></header>
<main><div class="grid" id="cards"></div><section class="card"><div class="label">Recent events and errors</div><pre id="events">loading...</pre></section><section class="card"><div class="label">Operations overview</div><pre id="overview">loading...</pre></section></main>
<script>
const q=id=>document.getElementById(id);const pretty=x=>JSON.stringify(x,null,2);
function state(v){return v===false?'bad':v===true?'ok':'warn'}
function card(label,value,cls='warn'){return `<div class="card"><div class="label">${label}</div><div class="value ${cls}">${value}</div></div>`}
async function get(path){const r=await fetch(path);if(!r.ok)throw Error(path+' '+r.status);return r.json()}
async function loadAll(){q('updated').textContent='refreshing';try{const [o,e]=await Promise.all([get('/operations/overview'),get('/operations/events')]);const safety=o.safety||{},runtime=o.local_runtime||{},obs=o.observation||{};q('cards').innerHTML=[card('Mode',o.mode||'UNKNOWN'),card('Runtime',runtime.runtime_status||'UNKNOWN',runtime.runtime_status==='PASS'?'ok':'warn'),card('Hermes',runtime.hermes_operational_state||'UNKNOWN',runtime.hermes_status==='OK'?'ok':'warn'),card('Ollama',String(runtime.ollama_available),state(runtime.ollama_available)),card('Execution allowed',String(safety.execution_allowed),state(safety.execution_allowed)),card('Market',obs.market_status||'UNKNOWN',obs.market_status==='OK'?'ok':'warn'),card('Risk gate',obs.risk_gate_status||'UNKNOWN',obs.risk_gate_status==='OK'?'ok':'warn'),card('Alerts',String(e.alerts_count),e.alerts_count?'warn':'ok')].join('');q('overview').textContent=pretty(o);q('events').textContent=pretty(e);q('updated').textContent='updated '+new Date().toLocaleTimeString()}catch(e){q('events').textContent='Dashboard data error: '+e.message;q('updated').textContent='error'}}
loadAll();setInterval(loadAll,30000);
</script></body></html>"""
