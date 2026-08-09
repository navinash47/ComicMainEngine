const $ = (id) => document.getElementById(id);

function money(n) {
  return `$${(Number(n) || 0).toFixed(4)}`;
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

function renderKpis(t) {
  const items = [
    ["Calls (window)", fmt(t.calls)],
    ["Spend", money(t.cost_usd)],
    ["Errors", fmt(t.errors)],
  ];
  $("kpis").innerHTML = items
    .map(([label, value]) => `<div class="kpi"><div class="label">${label}</div><div class="value">${value}</div></div>`)
    .join("");
}

function renderCatStats(rows) {
  $("catStats").innerHTML = (rows || []).length
    ? rows
        .map(
          (r) => `<div class="story-item static">
        <div class="story-phase">${esc(r.category)}</div>
        <div>
          <div class="title">${fmt(r.calls)} calls · ${Math.round((r.success_rate || 0) * 100)}% ok · avg ${fmt(r.avg_latency_ms)} ms</div>
          <div class="desc">in ${fmt(r.input_tokens)} · out ${fmt(r.output_tokens)} · img ${fmt(r.image_tokens)}</div>
        </div>
        <div class="pct">${money(r.cost_usd)}</div>
      </div>`
        )
        .join("")
    : `<p class="muted">No category stats yet.</p>`;
}

function renderRecs(recs) {
  $("recs").innerHTML = (recs || []).length
    ? recs
        .map((r) => {
          const o = r.optimal || {};
          return `<div class="story-item static">
            <div class="story-phase">${esc(r.category)}</div>
            <div>
              <div class="title">${esc(r.purpose)} → ${esc(o.model)} <span class="muted">(${esc(o.provider)})</span></div>
              <div class="desc">${esc(r.reason)} · n=${fmt(o.samples)} · avg ${money(o.avg_cost_usd)} · ${fmt(o.avg_latency_ms)}ms${
                o.avg_quality != null ? ` · QA ${o.avg_quality}` : ""
              }</div>
            </div>
            <div class="pct">use</div>
          </div>`;
        })
        .join("")
    : `<p class="muted">Need a few successful calls before recommendations appear.</p>`;
}

function renderImageQa(rows) {
  $("imageQa").innerHTML = (rows || []).length
    ? rows
        .map(
          (r) => `<div class="story-item static">
        <div class="story-phase">${esc(r.verdict)}</div>
        <div>
          <div class="title">${esc(r.model)} · ${esc(r.phase || "")}</div>
          <div class="desc">${esc(r.path || "")}</div>
        </div>
        <div class="pct">${r.score != null ? r.score : "—"}</div>
      </div>`
        )
        .join("")
    : `<p class="muted">No image QA yet — generate images or click Rescan.</p>`;
}

function renderCalls(rows) {
  $("calls").innerHTML = (rows || [])
    .map((r) => {
      const st = r.status === "ok" ? '<span class="ok">ok</span>' : `<span class="bad">error</span>`;
      const qa =
        r.image_quality_verdict != null
          ? `${esc(r.image_quality_verdict)} ${r.image_quality_score ?? ""}`
          : "—";
      return `<tr>
        <td>${esc((r.ts || "").replace("T", " ").slice(0, 19))}</td>
        <td>${esc(r.category)}</td>
        <td>${esc(r.phase)}</td>
        <td>${esc(r.provider)}</td>
        <td>${esc(r.model)}</td>
        <td>${esc(r.purpose)}</td>
        <td>${fmt(r.input_tokens)}</td>
        <td>${fmt(r.output_tokens)}</td>
        <td>${fmt(r.image_tokens)}</td>
        <td>${money(r.cost_usd)}</td>
        <td>${fmt(r.latency_ms)}</td>
        <td>${st}</td>
        <td>${qa}</td>
      </tr>`;
    })
    .join("");
}

async function tick() {
  const cat = $("catFilter").value;
  const q = cat && cat !== "all" ? `?category=${encodeURIComponent(cat)}&limit=300` : "?limit=300";
  try {
    const res = await fetch(`/api/analytics${q}`);
    const data = await res.json();
    renderKpis(data.stats?.totals || {});
    renderCatStats(data.stats?.by_category || []);
    renderRecs(data.recommendations || []);
    renderImageQa(data.stats?.image_quality || []);
    renderCalls(data.calls || []);
    $("updated").textContent = `updated ${new Date().toLocaleTimeString()}`;
  } catch (err) {
    $("updated").textContent = `offline: ${err}`;
  }
}

$("catFilter").addEventListener("change", tick);
$("rescanBtn").addEventListener("click", async () => {
  $("rescanBtn").disabled = true;
  try {
    await fetch("/api/analytics/rescan-images", { method: "POST" });
    await tick();
  } finally {
    $("rescanBtn").disabled = false;
  }
});

tick();
setInterval(tick, 3000);
