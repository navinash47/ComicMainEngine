const $ = (id) => document.getElementById(id);

function money(n, digits = 4) {
  return `$${(Number(n) || 0).toFixed(digits)}`;
}

function fmt(n) {
  return new Intl.NumberFormat().format(Number(n) || 0);
}

function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderKpis(t, unit) {
  const items = [
    ["Total spend", money(t.cost_usd, 3)],
    ["API calls", fmt(t.calls)],
    ["$/story (blend)", money(unit.cost_per_story_usd, 3)],
    ["$/panel (all-in)", money(unit.cost_per_panel_all_in_usd, 4)],
    ["Phase5 $/panel", money(unit.phase5_cost_per_panel_usd, 4)],
    ["100-ep project", money(unit.projected_100_episodes_usd, 2)],
  ];
  $("kpis").innerHTML = items
    .map(([label, value]) => `<div class="kpi"><div class="label">${label}</div><div class="value">${value}</div></div>`)
    .join("");
}

function renderBars(el, rows, labelKey, valueKey) {
  const max = Math.max(...rows.map((r) => Number(r[valueKey]) || 0), 0.0001);
  el.innerHTML = rows.length
    ? rows
        .map((r) => {
          const pct = Math.max(2, ((Number(r[valueKey]) || 0) / max) * 100);
          return `<div class="bar-row"><span>${esc(r[labelKey])}</span><div class="bar"><span style="width:${pct}%"></span></div><span>${money(r[valueKey])}</span></div>`;
        })
        .join("")
    : `<p class="muted">No data yet.</p>`;
}

function drawBarsCanvas(canvasId, rows, labelKey, valueKey, color = "#d9773a") {
  const canvas = $(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || 520;
  const cssH = 140;
  canvas.width = cssW * dpr;
  canvas.height = cssH * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssW, cssH);
  if (!rows.length) {
    ctx.fillStyle = "#b9a893";
    ctx.fillText("No series yet.", 12, 24);
    return;
  }
  const vals = rows.map((r) => Number(r[valueKey]) || 0);
  const max = Math.max(...vals, 0.0001);
  const pad = 18;
  const gap = 6;
  const n = rows.length;
  const barW = Math.max(8, (cssW - pad * 2 - gap * (n - 1)) / n);
  rows.forEach((r, i) => {
    const h = ((Number(r[valueKey]) || 0) / max) * (cssH - pad * 2);
    const x = pad + i * (barW + gap);
    const y = cssH - pad - h;
    ctx.fillStyle = color;
    ctx.fillRect(x, y, barW, h);
  });
}

function drawLineCanvas(canvasId, rows, xKey, yKey) {
  const canvas = $(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || 520;
  const cssH = 140;
  canvas.width = cssW * dpr;
  canvas.height = cssH * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssW, cssH);
  if (!rows.length) {
    ctx.fillStyle = "#b9a893";
    ctx.fillText("No daily spend yet.", 12, 24);
    return;
  }
  const vals = rows.map((r) => Number(r[yKey]) || 0);
  const max = Math.max(...vals, 0.0001);
  const pad = 16;
  const w = cssW - pad * 2;
  const h = cssH - pad * 2;
  ctx.strokeStyle = "rgba(243,230,212,0.12)";
  ctx.beginPath();
  ctx.moveTo(pad, pad);
  ctx.lineTo(pad, pad + h);
  ctx.lineTo(pad + w, pad + h);
  ctx.stroke();
  ctx.strokeStyle = "#e8b07a";
  ctx.lineWidth = 2;
  ctx.beginPath();
  rows.forEach((r, i) => {
    const x = pad + (i / Math.max(rows.length - 1, 1)) * w;
    const y = pad + h - (vals[i] / max) * h;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

async function load() {
  const res = await fetch("/api/roi");
  const data = await res.json();
  $("updated").textContent = data.server_time
    ? `as of ${new Date(data.server_time).toLocaleString()}`
    : "ready";

  const t = data.totals || {};
  const unit = data.unit_economics || {};
  renderKpis(t, unit);

  $("insights").innerHTML = (data.insights || [])
    .map((x) => `<li>${esc(x)}</li>`)
    .join("");

  $("units").innerHTML = [
    ["Stories in library", fmt(unit.stories)],
    ["Panels total", fmt(unit.panels)],
    ["Phase4 scripts $", money(unit.script_phase4_usd)],
    ["Phase5 batch $", money(unit.phase5_panel_batch_usd)],
    ["Compose/assemble API $", money(unit.compose_assemble_usd, 2)],
  ]
    .map(([k, v]) => `<div class="unit-card"><div class="label">${k}</div><div class="value">${v}</div></div>`)
    .join("");

  renderBars($("byPhase"), data.by_phase || [], "phase", "cost_usd");
  renderBars($("byProvider"), data.by_provider || [], "provider", "cost_usd");
  renderBars($("byCategory"), data.by_category || [], "category", "cost_usd");
  renderBars($("byPurpose"), data.by_purpose || [], "purpose", "cost_usd");

  drawBarsCanvas("phaseChart", data.by_phase || [], "phase", "cost_usd", "#d9773a");
  drawBarsCanvas("providerChart", data.by_provider || [], "provider", "cost_usd", "#8fcd9b");
  drawLineCanvas("dailyChart", data.daily || [], "day", "cost_usd");

  const recs = data.recommendations || [];
  $("recs").innerHTML = recs.length
    ? recs
        .map((r) => {
          const opt = r.optimal || {};
          return `<div class="rec-card">
            <div class="label">${esc(r.category)} · ${esc(r.purpose)}</div>
            <div><strong>${esc(opt.provider)} / ${esc(opt.model)}</strong></div>
            <div class="muted small">${money(opt.avg_cost_usd)} avg · ${fmt(opt.avg_latency_ms)} ms · ${esc(r.reason || "")}</div>
          </div>`;
        })
        .join("")
    : `<p class="muted">No recommendations yet.</p>`;
}

load();
setInterval(load, 15000);
