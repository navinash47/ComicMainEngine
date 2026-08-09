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

function authHeaders() {
  const pw = sessionStorage.getItem("ce_admin_pw") || "";
  return pw ? { "x-admin-password": pw } : {};
}

async function loadJson(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} ${res.status}`);
  return res.json();
}

function renderBars(el, rows) {
  const max = Math.max(...rows.map((r) => Number(r.cost_usd) || 0), 0.0001);
  el.innerHTML = rows.length
    ? rows
        .map((r) => {
          const pct = Math.max(2, ((Number(r.cost_usd) || 0) / max) * 100);
          return `<div class="bar-row"><span>${esc(r.phase)}</span><div class="bar"><span style="width:${pct}%"></span></div><span>${money(r.cost_usd)}</span></div>`;
        })
        .join("")
    : `<p class="muted">No usage yet.</p>`;
}

function renderFeedback(items, metaEl, listEl, source) {
  metaEl.textContent = `${items.length} responses · source ${source}`;
  listEl.innerHTML = items.length
    ? items
        .map((item) => {
          const panels = (item.panels || [])
            .map((p) => `P${p.index}:${p.rating}★ ${esc((p.feedback || "").slice(0, 60))}`)
            .join(" · ");
          return `<div class="fb-row">
            <div class="muted small">${esc(item.created_at)} · <strong>${esc(item.reviewer_name || item.reviewer_username || item.reviewer_email)}</strong> · ${esc(item.story_id)}</div>
            <p>Overall ${esc(item.overall_rating)}/5 — ${esc(item.overall_feedback || "")}</p>
            <p class="muted small">${panels}</p>
          </div>`;
        })
        .join("")
    : `<p class="muted">No reader feedback in snapshot yet. Deploy reader site and/or re-run prepare_admin_site.py</p>`;
}

async function maybeGate() {
  const gateInfo = await fetch("/api/gate").then((r) => r.json()).catch(() => ({ password_required: false }));
  if (!gateInfo.password_required) return true;
  if (sessionStorage.getItem("ce_admin_pw")) {
    const probe = await fetch("/api/gate", { headers: authHeaders() });
    if (probe.ok) return true;
  }
  $("gate").hidden = false;
  return new Promise((resolve) => {
    $("gateGo").onclick = async () => {
      const pw = $("gatePw").value;
      sessionStorage.setItem("ce_admin_pw", pw);
      const probe = await fetch("/api/gate", { headers: authHeaders() });
      if (!probe.ok) {
        $("gateErr").textContent = "Wrong password";
        return;
      }
      $("gate").hidden = true;
      resolve(true);
    };
  });
}

async function loadLiveFeedback() {
  const res = await fetch("/api/live-feedback", { headers: authHeaders() });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    $("fbMeta").textContent = data.detail || "live feedback unavailable";
    return;
  }
  if ((data.items || []).length) {
    renderFeedback(data.items, $("fbMeta"), $("feedback"), data.source || "upstash");
  }
}

async function main() {
  await maybeGate();
  const [overview, usage, roi, tasks, fbSnap] = await Promise.all([
    loadJson("/data/overview.json"),
    loadJson("/data/usage.json"),
    loadJson("/data/roi.json"),
    loadJson("/data/tasks.json"),
    loadJson("/data/story_feedback.json"),
  ]);

  $("exportedAt").textContent = `snapshot ${overview.exported_at || ""}`;
  if (overview.github) $("ghLink").href = overview.github;
  $("notes").innerHTML = (overview.notes || []).map((n) => `<li>${esc(n)}</li>`).join("");
  const rt = overview.routing || {};
  $("routing").textContent = `Text LLM: ${rt.text_llm || "—"} · Images: ${rt.images || "—"}`;

  const t = usage.totals || {};
  $("kpis").innerHTML = [
    ["Total spend", money(t.cost_usd)],
    ["API calls", fmt(t.calls)],
    ["Input tokens", fmt(t.input_tokens)],
    ["Output tokens", fmt(t.output_tokens)],
    ["Errors", fmt(t.errors)],
  ]
    .map(([label, value]) => `<div class="kpi"><div class="label">${label}</div><div class="value">${value}</div></div>`)
    .join("");

  $("phases").innerHTML = (overview.phases || [])
    .map((p) => `<div class="task"><span>${esc(p.id)} — ${esc(p.title)}</span><span class="status ${esc(p.status)}">${esc(p.status)}</span></div>`)
    .join("");

  renderBars($("byPhase"), usage.by_phase || []);

  $("tasks").innerHTML = (tasks.tasks || [])
    .slice(0, 20)
    .map(
      (task) =>
        `<div class="task"><span>${esc(task.title)}</span><span class="status ${esc(task.status)}">${esc(task.status)}</span></div>`
    )
    .join("");

  const unit = roi.unit_economics || {};
  $("roi").textContent = JSON.stringify(
    {
      cost_per_story_usd: unit.cost_per_story_usd,
      cost_per_panel_all_in_usd: unit.cost_per_panel_all_in_usd,
      projected_100_episodes_usd: unit.projected_100_episodes_usd,
      insights: (roi.insights || []).slice(0, 5),
    },
    null,
    2
  );

  renderFeedback(fbSnap.items || [], $("fbMeta"), $("feedback"), "snapshot");
  $("refreshLive").onclick = () => loadLiveFeedback();
  loadLiveFeedback();
}

main().catch((err) => {
  document.body.insertAdjacentHTML(
    "beforeend",
    `<p class="muted" style="padding:1.5rem">Failed to load admin data: ${esc(err.message)}. Run <code>python scripts/prepare_admin_site.py</code> then redeploy.</p>`
  );
});
