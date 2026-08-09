const $ = (id) => document.getElementById(id);

function money(n) {
  return `$${(Number(n) || 0).toFixed(4)}`;
}

function fmt(n) {
  return new Intl.NumberFormat().format(Number(n) || 0);
}

function renderKpis(t) {
  const items = [
    ["Total spend", money(t.cost_usd)],
    ["API calls", fmt(t.calls)],
    ["Input tokens", fmt(t.input_tokens)],
    ["Output tokens", fmt(t.output_tokens)],
    ["Image tokens", fmt(t.image_tokens)],
    ["Errors", fmt(t.errors)],
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
          return `<div class="bar-row"><span>${r[labelKey]}</span><div class="bar"><span style="width:${pct}%"></span></div><span>${money(r[valueKey])}</span></div>`;
        })
        .join("")
    : `<p style="color:var(--muted)">No data yet — run phase1 / ping.</p>`;
}

function renderRecent(rows) {
  $("recent").innerHTML = rows
    .map((r) => {
      const ok = r.ok ? '<span class="ok">yes</span>' : `<span class="bad">no</span>`;
      return `<tr>
        <td>${(r.ts || "").replace("T", " ").slice(0, 19)}</td>
        <td>${r.phase || ""}</td>
        <td>${r.provider || ""}</td>
        <td>${r.model || ""}</td>
        <td>${fmt(r.input_tokens)}</td>
        <td>${fmt(r.output_tokens)}</td>
        <td>${fmt(r.image_tokens)}</td>
        <td>${money(r.cost_usd)}</td>
        <td>${fmt(r.latency_ms)}</td>
        <td>${ok}</td>
      </tr>`;
    })
    .join("");
}

function renderTasks(snap) {
  if (!snap) return;
  const pct = Math.round((Number(snap.completion_ratio) || 0) * 100);
  $("taskPct").textContent = `${pct}% done`;
  $("taskBar").style.width = `${pct}%`;
  const c = snap.counts || {};
  $("taskCounts").innerHTML = ["completed", "in_progress", "pending", "failed", "blocked"]
    .map((k) => `<span>${k}: <strong style="color:var(--ink)">${c[k] || 0}</strong></span>`)
    .join("");
  $("taskList").innerHTML = (snap.tasks || [])
    .map((t) => {
      const note = (t.meta && (t.meta.last_note || t.meta.error)) || t.description || "";
      const p = Math.round((Number(t.progress) || 0) * 100);
      return `<li class="task-item">
        <div class="status ${t.status}">${t.status.replace("_", " ")}</div>
        <div>
          <div class="title">${t.title}</div>
          <div class="desc">${note}</div>
        </div>
        <div class="pct">${p}%</div>
      </li>`;
    })
    .join("");
}

function drawChart(series) {
  const canvas = $("chart");
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || 600;
  const cssH = 160;
  canvas.width = cssW * dpr;
  canvas.height = cssH * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssW, cssH);

  if (!series.length) {
    ctx.fillStyle = "#b9a893";
    ctx.fillText("Spend series appears after calls land in SQLite.", 12, 28);
    return;
  }

  const vals = series.map((s) => Number(s.cost_usd) || 0);
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

  ctx.strokeStyle = "#d9773a";
  ctx.lineWidth = 2;
  ctx.beginPath();
  series.forEach((s, i) => {
    const x = pad + (i / Math.max(series.length - 1, 1)) * w;
    const y = pad + h - (vals[i] / max) * h;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

async function tick() {
  try {
    const res = await fetch("/api/summary");
    const data = await res.json();
    renderKpis(data.totals || {});
    renderTasks(data.taskobserver);
    renderBars($("byProvider"), data.by_provider || [], "provider", "cost_usd");
    renderBars($("byPhase"), data.by_phase || [], "phase", "cost_usd");
    renderRecent(data.recent || []);
    drawChart(data.series || []);
    $("liveDot").classList.add("on");
    $("updated").textContent = `updated ${new Date().toLocaleTimeString()} · ${data.db_path || ""}`;
  } catch (err) {
    $("liveDot").classList.remove("on");
    $("updated").textContent = `offline: ${err}`;
  }
}

$("refreshTasks").addEventListener("click", async () => {
  await fetch("/api/tasks/refresh", { method: "POST" });
  tick();
});

tick();
setInterval(tick, 2000);
window.addEventListener("resize", () => tick());
