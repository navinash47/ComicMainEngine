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
  const scene = data.test_scene || {};
  const series = data.test_series || {};
  const episodes = series.episodes || [];
  const prove = (data.ep01 && data.ep01.b1_prove) || {};
  const active = program.active_phase_id || "—";

  $("lede").textContent =
    (program.notes && program.notes[0]) ||
    "Parallel 3D-previs track beside Version 2 and 2A.";
  $("kpis").innerHTML = [
    kpi("Program", program.version || "2B"),
    kpi("Active", String(active).toUpperCase()),
    kpi("Phases done", `${done}/${phases.length}`),
    kpi("Fixture", "HIMYM ep1"),
    kpi("Panels", String(series.panel_count || data.ep01?.panel_count || "—")),
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

  $("sceneMeta").textContent = series.title
    ? `${series.title} · ${series.panel_count || 0} panels`
    : scene.title || "No test series";
  $("sceneNote").textContent = series.product_claim || scene.product_claim || "";
  const epCards = episodes
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
  const proveCard = prove.panel_index
    ? `<article class="v2a-ep">
        <div class="v2a-ep-num">P${esc(prove.panel_index)}</div>
        <div>
          <h3>B1 prove · panel ${esc(prove.panel_index)}</h3>
          <p><span class="muted">Location</span> ${esc(prove.location_id || scene.location_id || "—")}</p>
          <p><span class="muted">Cast</span> ${(prove.characters || scene.characters || []).map(esc).join(", ") || "—"}</p>
          <p><span class="muted">Camera</span> ${esc(prove.camera || "")}</p>
          <p><span class="muted">Light</span> ${esc(prove.lighting || "")}</p>
          <p><span class="muted">Blocking</span> ${esc(prove.blocking || "")}</p>
          <p><span class="muted">Scene</span> ${esc(prove.scene || scene.description || "")}</p>
          <p><span class="muted">Output</span> ${esc(prove.output || scene.b1_output || "—")}</p>
        </div>
      </article>`
    : "";
  $("sceneDetail").innerHTML = epCards + proveCard || "";

  $("updated").textContent = program.updated_at
    ? `updated ${program.updated_at}`
    : "loaded";

  highlightPipeline(active, data.phases || {});
}

function highlightPipeline(activeId, phases) {
  const order = ["b1", "b2", "b3", "g1", "b4", "b5", "b6", "g2", "b8"];
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
    const res = await fetch("/api/v2b/program");
    if (!res.ok) throw new Error(`${res.status}`);
    render(await res.json());
    await loadB4();
    await loadB5();
    await loadB6();
    await loadG2();
  } catch (err) {
    $("updated").textContent = `error ${err}`;
    $("lede").textContent = "Could not load data/v2b_program.json.";
  }
}

$("refreshBtn").addEventListener("click", load);
load();

async function loadB4() {
  const compare = $("b4Compare");
  const turn = $("b4Turntable");
  if (!compare) return;
  try {
    const res = await fetch("/api/v2b/b4/gallery");
    if (!res.ok) return;
    const g = await res.json();
    const fig = (src, cap) =>
      src
        ? `<figure style="margin:0;background:var(--bg1);border:1px solid var(--line);padding:0.4rem"><img src="${esc(src)}" alt="${esc(cap)}" style="width:100%;height:auto;display:block;background:#111"/><figcaption class="muted small">${esc(cap)}</figcaption></figure>`
        : "";
    compare.style.display = "grid";
    compare.style.gridTemplateColumns = "1fr 1fr 1fr";
    compare.style.gap = "0.75rem";
    compare.innerHTML = [
      fig(g.b3_cam_a, "B3 / G1 cam_a (frozen)"),
      fig(g.b4_beauty_a, "B4 beauty cam_a"),
      fig(g.b4_cam_a, "B4 panel cam_a (style+Dad LoRA)"),
    ].join("");
    if (turn) {
      turn.style.display = "grid";
      turn.style.gridTemplateColumns = "repeat(auto-fill, minmax(140px, 1fr))";
      turn.style.gap = "0.5rem";
      turn.style.marginTop = "0.75rem";
      const shots = (g.stylized || []).length ? g.stylized : g.turntable || [];
      turn.innerHTML = shots.map((u, i) => fig(u, `dad ${i + 1}`)).join("");
    }
  } catch {
    /* gallery is optional until B4 PNGs exist */
  }
}

async function loadB5() {
  const el = $("b5Compare");
  if (!el) return;
  try {
    const res = await fetch("/api/v2b/b5/gallery");
    if (!res.ok) return;
    const g = await res.json();
    const fig = (src, cap) =>
      src
        ? `<figure style="margin:0;background:var(--bg1);border:1px solid var(--line);padding:0.4rem"><img src="${esc(src)}" alt="${esc(cap)}" style="width:100%;height:auto;display:block;background:#111"/><figcaption class="muted small">${esc(cap)}</figcaption></figure>`
        : "";
    el.style.display = "grid";
    el.style.gridTemplateColumns = "1fr 1fr 1fr";
    el.style.gap = "0.75rem";
    el.innerHTML = [
      fig(g.living_a, "living_room cam_a (spec + Dad LoRA)"),
      fig(g.lobby_wide, "Grand Oriole lobby wide"),
      fig(g.lobby_close, "Grand Oriole lobby close"),
    ].join("");
  } catch {
    /* optional until B5 PNGs exist */
  }
}

async function loadB6() {
  const el = $("b6Compare");
  if (!el) return;
  try {
    const res = await fetch("/api/v2b/b6/gallery");
    if (!res.ok) return;
    const g = await res.json();
    const fig = (src, cap) =>
      src
        ? `<figure style="margin:0;background:var(--bg1);border:1px solid var(--line);padding:0.4rem"><img src="${esc(src)}" alt="${esc(cap)}" style="width:100%;height:auto;display:block;background:#111"/><figcaption class="muted small">${esc(cap)}</figcaption></figure>`
        : "";
    el.style.display = "grid";
    el.style.gridTemplateColumns = "1fr 1fr 1fr 1fr";
    el.style.gap = "0.75rem";
    el.innerHTML = [
      fig(g.cam_a_pass1, "cam_a pass1 (style+Dad)"),
      fig(g.cam_a, "cam_a two-pass (Maya mask)"),
      fig(g.cam_c_pass1, "cam_c pass1 (style+Dad)"),
      fig(g.cam_c, "cam_c two-pass (Maya mask)"),
    ].join("");
  } catch {
    /* optional until B6 PNGs exist */
  }
}

async function loadG2() {
  const el = $("g2Compare");
  if (!el) return;
  try {
    const res = await fetch("/api/v2b/g2/gallery");
    if (!res.ok) return;
    const g = await res.json();
    const fig = (src, cap) =>
      src
        ? `<figure style="margin:0;background:var(--bg1);border:1px solid var(--line);padding:0.4rem"><img src="${esc(src)}" alt="${esc(cap)}" style="width:100%;height:auto;display:block;background:#111"/><figcaption class="muted small">${esc(cap)}</figcaption></figure>`
        : "";
    el.style.display = "grid";
    el.style.gridTemplateColumns = "1fr 1fr 1fr 1fr";
    el.style.gap = "0.75rem";
    el.innerHTML = [
      fig(g.beauty_a, "G2 beauty cam_a (Kenney CC0)"),
      fig(g.cam_a, "cam_a two-pass (ce_maya_gltf mask)"),
      fig(g.cam_c, "cam_c two-pass"),
      fig(g.stylized, "stylized standing Dad"),
    ].join("");
  } catch {
    /* optional until G2 PNGs exist */
  }
}
