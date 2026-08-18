const $ = (id) => document.getElementById(id);

function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function kpi(label, value) {
  return `<div class="kpi"><div class="label">${esc(label)}</div><div class="value">${esc(value)}</div></div>`;
}

function render(data) {
  const program = data.program || {};
  const ids = data.phase_ids || [];
  const phases = ids.map((id) => data.phases?.[id]).filter(Boolean);
  const done = phases.filter((p) => p.status === "complete").length;
  const pct = phases.length ? Math.round((100 * done) / phases.length) : 0;
  const series = data.test_series || {};
  const episodes = series.episodes || [];
  const active = program.active_phase_id || "—";

  $("lede").textContent =
    (program.notes && program.notes[0]) ||
    "Parallel storyboard-first track beside Version 2.";
  $("kpis").innerHTML = [
    kpi("Program", program.version || "2A"),
    kpi("Active", String(active).toUpperCase()),
    kpi("Phases done", `${done}/${phases.length}`),
    kpi("Test episodes", String(series.episode_count || episodes.length || 0)),
    kpi("Tone", series.tone || "—"),
  ].join("");

  $("phasePct").textContent = `${pct}%`;
  $("phaseBar").style.width = `${pct}%`;
  $("phaseList").innerHTML = phases
    .map((p) => {
      const checks = p.checklist || [];
      const checked = new Set(p.checklist_done || []);
      const items = checks
        .map((c) => {
          const on = checked.has(c);
          return `<li class="${on ? "on" : ""}">${on ? "✓" : "○"} ${esc(c)}</li>`;
        })
        .join("");
      const notes = (p.notes || []).map((n) => `<p class="muted small">${esc(n)}</p>`).join("");
      return `<article class="v2a-phase status-${esc(p.status)}">
        <div class="v2a-phase-head">
          <span class="v2a-id">${esc(p.id)}</span>
          <h3>${esc(p.title)}</h3>
          <span class="v2a-status ${esc(p.status)}">${esc(p.status)}</span>
        </div>
        <p class="muted small">${esc(p.track)} · ${esc(p.exit_gate)}</p>
        <ul class="v2a-checks">${items}</ul>
        ${notes}
      </article>`;
    })
    .join("");

  $("seriesMeta").textContent = series.title
    ? `${series.title} · ${series.epic || ""} / ${series.book || ""}`
    : "No test series";
  $("seriesNote").textContent = series.product_claim || "";
  $("episodeList").innerHTML = episodes
    .map(
      (ep) => `<article class="v2a-ep">
        <div class="v2a-ep-num">${esc(ep.n)}</div>
        <div>
          <h3>${esc(ep.title)}</h3>
          <p><span class="muted">Story</span> ${esc(ep.story_goal)}</p>
          <p><span class="muted">Framework</span> ${esc(ep.framework_goal)}</p>
          <p><span class="muted">Gate</span> ${esc(ep.gate)}</p>
        </div>
      </article>`
    )
    .join("");

  $("updated").textContent = program.updated_at
    ? `updated ${program.updated_at}`
    : "loaded";

  highlightPipeline(active, data.phases || {});
}

function highlightPipeline(activeId, phases) {
  const order = ["a1", "a2", "a3", "a4", "a5"];
  const activeIdx = order.indexOf(activeId);
  document.querySelectorAll("#pipelineFlow .v2a-node").forEach((el) => {
    const id = el.getAttribute("data-phase");
    el.classList.remove("on", "done");
    const st = phases[id]?.status;
    if (st === "complete") el.classList.add("done");
    if (id === activeId || (st !== "complete" && order.indexOf(id) === activeIdx)) {
      el.classList.add("on");
    }
  });
  const hint = $("archHint");
  if (hint) hint.textContent = `active ${String(activeId || "—").toUpperCase()}`;
}

function wireArchTabs() {
  const tabs = document.querySelectorAll("[data-arch]");
  const panes = document.querySelectorAll("[data-pane]");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const id = tab.getAttribute("data-arch");
      tabs.forEach((t) => t.classList.toggle("on", t === tab));
      panes.forEach((p) => p.classList.toggle("on", p.getAttribute("data-pane") === id));
    });
  });
}

wireArchTabs();

async function load() {
  $("updated").textContent = "loading…";
  try {
    const res = await fetch("/api/v2a/program");
    if (!res.ok) throw new Error(`${res.status}`);
    render(await res.json());
  } catch (err) {
    $("updated").textContent = `error ${err}`;
    $("lede").textContent = "Could not load data/v2a_program.json.";
  }
}

$("refreshBtn").addEventListener("click", load);
load();
