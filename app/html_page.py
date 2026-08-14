#!/usr/bin/env python3
"""Static HTML dashboard for the gateway."""
from __future__ import annotations
import html
import json


def _esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def render_index(app) -> str:
    cfg = app.public_config()
    state_json = json.dumps(cfg, ensure_ascii=False)
    return PAGE.replace("__STATE_JSON__", state_json)


PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VPN Subscription Gateway</title>
<style>
:root { --bg:#0b0f17; --card:#131a26; --line:#1f2937; --fg:#e5e7eb; --dim:#9ca3af;
        --acc:#3b82f6; --ok:#22c55e; --bad:#ef4444; --warn:#f59e0b; }
* { box-sizing:border-box; margin:0; padding:0; }
body { background:var(--bg); color:var(--fg); font:14px/1.5 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif; padding:24px; }
.wrap { max-width:1200px; margin:0 auto; }
h1 { font-size:20px; margin-bottom:4px; }
.sub { color:var(--dim); font-size:13px; margin-bottom:20px; }
.grid { display:grid; grid-template-columns:1fr 320px; gap:16px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px; margin-bottom:16px; }
.card h2 { font-size:14px; margin-bottom:10px; color:var(--dim); font-weight:600; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th, td { text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); white-space:nowrap; }
th { color:var(--dim); font-weight:500; }
tr:hover td { background:#182136; }
.badge { display:inline-block; padding:1px 8px; border-radius:20px; font-size:12px; }
.ok { background:#052e16; color:var(--ok); }
.bad { background:#450a0a; color:var(--bad); }
.warn { background:#451a03; color:var(--warn); }
button { background:#1e293b; color:var(--fg); border:1px solid var(--line); border-radius:6px;
         padding:4px 10px; font-size:12px; cursor:pointer; }
button:hover { border-color:var(--acc); }
button.acc { background:var(--acc); border-color:var(--acc); color:#fff; }
button.sel { background:#052e16; border-color:var(--ok); color:var(--ok); }
.muted { color:var(--dim); font-size:12px; }
.mono { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; }
.filters { display:flex; gap:8px; margin-bottom:10px; flex-wrap:wrap; align-items:center; }
input, select { background:#0f172a; color:var(--fg); border:1px solid var(--line); border-radius:6px;
                padding:4px 8px; font-size:12px; }
.subbox { background:#0f172a; border:1px solid var(--line); border-radius:6px; padding:8px; font-size:12px;
           word-break:break-all; margin-bottom:8px; }
.tunnel { display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px solid var(--line); }
.tunnel:last-child { border-bottom:none; }
.pill { display:inline-block; min-width:56px; text-align:center; }
.tabbar { display:flex; gap:6px; margin-bottom:12px; }
.tab { padding:6px 14px; border:1px solid var(--line); border-radius:8px; cursor:pointer; color:var(--dim); background:transparent; }
.tab.active { background:var(--acc); color:#fff; border-color:var(--acc); }
#toast { position:fixed; top:16px; right:16px; background:#134e4a; color:#ccfbf1; padding:8px 14px;
         border-radius:8px; font-size:13px; opacity:0; transition:opacity .3s; z-index:99; }
</style>
</head>
<body>
<div class="wrap">
  <h1>🌐 VPN Subscription Gateway</h1>
  <div class="sub">免费 VPNGate 节点聚合 · 自选节点 · 生成 Clash/v2rayN 订阅</div>

  <div class="grid">
    <div>
      <div class="card">
        <h2>节点列表 <span class="muted" id="nodecount"></span></h2>
        <div class="filters">
          <select id="country"><option value="">全部国家</option></select>
          <select id="sort">
            <option value="latency">按延迟</option>
            <option value="score">按评分</option>
          </select>
          <label class="muted"><input type="checkbox" id="onlyreach" checked> 只看可达</label>
          <span style="flex:1"></span>
          <button onclick="refreshNodes()">⟳ 拉取节点</button>
        </div>
        <div style="overflow-x:auto"><table id="nodelist">
          <thead><tr><th></th><th>国家</th><th>主机</th><th>IP</th><th>延迟</th><th>评分</th><th>在线</th><th>操作</th></tr></thead>
          <tbody></tbody>
        </table></div>
      </div>
    </div>

    <div>
      <div class="card">
        <h2>自选节点</h2>
        <div class="filters">
          <select id="autocc"><option value="">热门国家…</option></select>
          <input id="autolimit" type="number" value="3" min="1" max="16" style="width:64px">
          <button class="acc" onclick="autoSelect()">自动挑选</button>
        </div>
        <div id="selectedbox"></div>
        <div style="margin-top:10px">
          <button onclick="reconnectAll()">🔄 全部重连</button>
        </div>
      </div>

      <div class="card">
        <h2>订阅链接</h2>
        <div class="muted" style="margin-bottom:6px">服务器: <span class="mono" id="serverip">…</span></div>
        <div class="subbox mono" id="subinfo">加载中…</div>
        <div style="display:flex; gap:8px; flex-wrap:wrap">
          <button onclick="copySub('clash')">复制 Clash</button>
          <button onclick="copySub('v2ray')">复制 v2rayN</button>
          <button onclick="copySub('base64')">复制 Base64</button>
        </div>
      </div>

      <div class="card">
        <h2>隧道状态</h2>
        <div id="tunnels">加载中…</div>
      </div>
    </div>
  </div>
</div>
<div id="toast"></div>
<script>
let STATE = __STATE_JSON__;
let NODES = [];
let SELECTED = [];

function toast(msg){ const t=document.getElementById('toast'); t.textContent=msg; t.style.opacity=1;
  setTimeout(()=>t.style.opacity=0, 2000); }

async function api(path, opts){
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function flag(cc){
  const m = (cc||'').toUpperCase();
  const off = 127397;
  if (m.length !== 2) return '';
  const cp = m.charCodeAt(0), cp2 = m.charCodeAt(1);
  if (cp<65||cp>90||cp2<65||cp2>90) return '';
  return String.fromCodePoint(cp+off, cp2+off);
}

async function refreshNodes(){
  toast('正在拉取并测速…');
  try {
    await api('/api/refresh', {method:'POST'});
    await loadNodes();
    toast('节点已刷新');
  } catch(e){ toast('刷新失败: '+e.message); }
}

async function loadNodes(){
  try {
    const q = new URLSearchParams();
    const cc = document.getElementById('country').value;
    if (cc) q.set('country', cc);
    if (document.getElementById('onlyreach').checked) q.set('reachable','1');
    const data = await api('/api/nodes?'+q.toString());
    NODES = data.nodes;
    document.getElementById('nodecount').textContent = '('+data.total+' 个)';
    renderNodes();
  } catch(e){ toast('加载节点失败: '+e.message); }
}

function renderNodes(){
  const sort = document.getElementById('sort').value;
  let ns = [...NODES];
  ns.sort((a,b)=>{
    if (sort==='score') return parseInt(b.score||0)-parseInt(a.score||0);
    const la = a.latency_ms==null?1e9:a.latency_ms, lb = b.latency_ms==null?1e9:b.latency_ms;
    return la-lb;
  });
  const tb = document.querySelector('#nodelist tbody');
  tb.innerHTML = '';
  ns.slice(0, 200).forEach(n=>{
    const sel = SELECTED.includes(n.id);
    const tr = document.createElement('tr');
    const lat = n.latency_ms==null ? '<span class="badge bad">不可达</span>' : Math.round(n.latency_ms)+'ms';
    tr.innerHTML = '<td>'+flag(n.country_short)+'</td>'+
      '<td>'+n.country_short+'</td>'+
      '<td>'+esc(n.hostname)+'</td>'+
      '<td class="mono">'+esc(n.ip)+'</td>'+
      '<td>'+lat+'</td>'+
      '<td>'+esc(n.score)+'</td>'+
      '<td>'+esc(n.users||'')+'</td>'+
      '<td><button class="'+(sel?'sel':'')+'" onclick="toggleSel(\''+esc(n.id).replace(/'/g,"\\'")+'\')">'+(sel?'✓ 已选':'选择')+'</button></td>';
    tb.appendChild(tr);
  });
}

function esc(s){ const d=document.createElement('div'); d.textContent=s==null?'':String(s); return d.innerHTML; }

async function toggleSel(id){
  try {
    await api('/api/select', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({node_id:id, action:'toggle'})});
    await loadSelected(); await loadNodes();
  } catch(e){ toast('操作失败: '+e.message); }
}

async function autoSelect(){
  const cc = document.getElementById('autocc').value;
  const limit = parseInt(document.getElementById('autolimit').value)||3;
  if (!cc){ toast('请选择国家'); return; }
  try {
    await api('/api/select', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({country:cc, limit:limit, action:'replace'})});
    await loadSelected(); await loadNodes();
    toast('已挑选 '+cc+' 节点');
  } catch(e){ toast('失败: '+e.message); }
}

async function loadSelected(){
  const data = await api('/api/status');
  SELECTED = data.selected || [];
  renderSelected(data);
  renderTunnels(data.tunnels);
  if (data.public_ip) document.getElementById('serverip').textContent = data.public_ip;
  renderSub();
}

function renderSelected(data){
  const box = document.getElementById('selectedbox');
  if (!SELECTED.length){ box.innerHTML = '<div class="muted">尚未选择节点 — 从左侧列表选择,或按国家自动挑选。</div>'; return; }
  const byId = {}; NODES.forEach(n=>byId[n.id]=n);
  const aliveSet = new Set((data.tunnels.tunnels||[]).filter(t=>t.alive).map(t=>t.node_id));
  box.innerHTML = SELECTED.map(id=>{
    const n = byId[id];
    const name = n ? (flag(n.country_short)+' '+n.country_short+' '+(n.hostname||'')) : id;
    const alive = aliveSet.has(id);
    return '<div class="tunnel"><span>'+(alive?'<span class="pill badge ok">UP</span>':'<span class="pill badge bad">DOWN</span>')+' '+esc(name)+'</span>'+
      '<button onclick="toggleSel(\''+esc(id).replace(/'/g,"\\'")+'\')">移除</button></div>';
  }).join('');
}

function renderTunnels(summary){
  const box = document.getElementById('tunnels');
  const list = summary && summary.tunnels ? summary.tunnels : [];
  if (!list.length){ box.innerHTML = '<div class="muted">暂无隧道。</div>'; return; }
  box.innerHTML = list.map(t=>{
    return '<div class="tunnel"><span>'+(t.alive?'<span class="pill badge ok">UP</span>':'<span class="pill badge bad">DOWN</span>')+
      ' '+esc(t.label)+' <span class="muted">:'+t.port+'</span></span>'+
      '<span class="mono muted">'+(t.exit_ip||'')+'</span></div>';
  }).join('');
}

function renderSub(){
  const server = document.getElementById('serverip').textContent || 'SERVER_IP';
  const box = document.getElementById('subinfo');
  let lines = [];
  SELECTED.forEach(id=>{
    const n = NODES.find(x=>x.id===id);
    if (!n) return;
    lines.push('socks5://USER:PASS@'+server+':PORT  # '+flag(n.country_short)+' '+n.hostname);
  });
  box.textContent = lines.length ? lines.join('\n') : '选择节点后生成订阅';
}

function subUrl(fmt){
  const base = location.origin;
  return base+'/sub/'+fmt;
}

async function copySub(fmt){
  const url = subUrl(fmt);
  try {
    await navigator.clipboard.writeText(url);
    toast('已复制: '+url);
  } catch(e){
    prompt('订阅链接(复制):', url);
  }
}

async function reconnectAll(){
  try { await api('/api/reconnect', {method:'POST'}); toast('已触发重连'); await loadSelected(); }
  catch(e){ toast('失败: '+e.message); }
}

async function loadCountries(){
  const data = await api('/api/countries');
  const sel = document.getElementById('country');
  const auto = document.getElementById('autocc');
  const hot = ['JP','US','KR','SG','HK','TW','GB','DE','FR','NL','CA','AU','TH'];
  data.forEach(c=>{
    const o = document.createElement('option'); o.value=c.code; o.textContent=c.code+' ('+c.count+')';
    sel.appendChild(o);
    if (hot.includes(c.code)){ const a=o.cloneNode(); auto.appendChild(a); }
  });
}

document.getElementById('country').addEventListener('change', loadNodes);
document.getElementById('sort').addEventListener('change', renderNodes);
document.getElementById('onlyreach').addEventListener('change', loadNodes);

(async function init(){
  try {
    await loadCountries();
    await loadNodes();
    await loadSelected();
  } catch(e){ toast('初始化失败: '+e.message); }
  setInterval(async ()=>{ try{ await loadSelected(); }catch(e){} }, 5000);
})();
</script>
</body>
</html>
""";
