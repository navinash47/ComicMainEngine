const $ = (id) => document.getElementById(id);

function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}
function fmt(n) {
  return new Intl.NumberFormat().format(Number(n) || 0);
}
function stars(n) {
  const v = Number(n) || 0;
  return "★".repeat(Math.round(v)) + "☆".repeat(Math.max(0, 5 - Math.round(v)));
}

let peopleCache = [];
let selectedId = null;
let lastPayload = null;

function renderPeople(people) {
  peopleCache = people || [];
  $("peopleList").innerHTML = peopleCache.length
    ? peopleCache
        .map((p) => {
          const on = p.id === selectedId ? "on" : "";
          return `<button type="button" class="person-chip ${on}" data-id="${esc(p.id)}">
            <strong>${esc(p.name || "anon")}</strong>
            <span class="muted small">stories ${fmt(p.stories_rated)} · Q ${fmt(p.questionnaire_count)} · avg ${p.avg_overall ?? "—"}</span>
          </button>`;
        })
        .join("")
    : `<p class="muted">No reviewers yet — send people to <a href="/review">/review</a>.</p>`;

  $("peopleList").querySelectorAll(".person-chip").forEach((btn) => {
    btn.onclick = () => {
      selectedId = btn.dataset.id;
      renderPeople(peopleCache);
      showPerson(selectedId);
    };
  });
  if (!selectedId && peopleCache[0]) {
    selectedId = peopleCache[0].id;
    renderPeople(peopleCache);
  } else if (selectedId) {
    showPerson(selectedId);
  }
}

function showPerson(id) {
  const p = peopleCache.find((x) => x.id === id);
  if (!p) {
    $("personDetail").innerHTML = `<p class="muted">Select a person.</p>`;
    return;
  }
  const stories = p.story_responses || [];
  const qs = p.questionnaires || [];
  $("personDetail").innerHTML = `
    <div class="person-head">
      <div>
        <h3>${esc(p.name || "anon")}</h3>
        <p class="muted small">${esc(p.email || p.id)}</p>
      </div>
      <div class="person-stats">
        <div><span class="label">Stories rated</span><strong>${fmt(p.stories_rated)}</strong></div>
        <div><span class="label">Mom Test</span><strong>${fmt(p.questionnaire_count)}</strong></div>
        <div><span class="label">Avg overall</span><strong>${p.avg_overall != null ? p.avg_overall + " " + stars(p.avg_overall) : "—"}</strong></div>
      </div>
    </div>
    <h2 class="fb-section">Story ratings</h2>
    ${
      stories.length
        ? stories
            .map((item) => {
              const panels = (item.panels || [])
                .map((pn) => `<li><strong>P${esc(pn.index)}</strong> ${esc(pn.rating)}★ — ${esc(pn.feedback || "—")}</li>`)
                .join("");
              return `<article class="fb-card">
                <div class="muted small">${esc((item.created_at || "").replace("T", " ").slice(0, 19))} · ${esc(item.story_id)}</div>
                <p><strong>Overall ${esc(item.overall_rating)}/5</strong> ${stars(item.overall_rating)}</p>
                <p>${esc(item.overall_feedback || "(no written overall)")}</p>
                <ul class="panel-fb">${panels || "<li class='muted'>No panel notes</li>"}</ul>
              </article>`;
            })
            .join("")
        : `<p class="muted">No story ratings.</p>`
    }
    <h2 class="fb-section">Mom Test questionnaire</h2>
    ${
      qs.length
        ? qs
            .map((item) => {
              const answers = item.answers || {};
              const rows = Object.entries(answers)
                .filter(([k]) => !k.startsWith("_"))
                .map(([k, v]) => `<div class="q-ans"><div class="muted small">${esc(k)}</div><p>${esc(v)}</p></div>`)
                .join("");
              return `<article class="fb-card">
                <div class="muted small">${esc((item.created_at || "").replace("T", " ").slice(0, 19))} · ${esc(item.story_id || "—")}</div>
                ${rows || "<p class='muted'>Empty</p>"}
              </article>`;
            })
            .join("")
        : `<p class="muted">No Mom Test form yet.</p>`
    }`;
}

function drawCharts(charts) {
  if (!window.Charts) return;
  const hist = (charts && charts.ratings_hist) || [0, 0, 0, 0, 0];
  Charts.bar($("ratingChart"), ["1★", "2★", "3★", "4★", "5★"], hist);
  const stories = (charts && charts.by_story) || [];
  Charts.bar(
    $("storyChart"),
    stories.map((s) => String(s.story_id).replace("episode_", "").slice(0, 10)),
    stories.map((s) => s.avg_overall),
    { max: 5 }
  );
}

async function loadCrm() {
  const res = await fetch("/api/admin/crm");
  const data = await res.json();
  if (!res.ok) {
    $("rvMeta").textContent = data.detail || "failed to load CRM";
    return;
  }
  lastPayload = data;
  const s = data.summary || {};
  $("rvMeta").textContent = `${fmt(s.people)} people · ${fmt(s.story_feedback)} story ratings · ${fmt(s.questionnaires)} Mom Test forms`;
  $("crmKpis").innerHTML = [
    ["People", fmt(s.people)],
    ["Story ratings", fmt(s.story_feedback)],
    ["Mom Test forms", fmt(s.questionnaires)],
    ["Registered reviewers", fmt(s.reviewers)],
  ]
    .map(([label, value]) => `<div class="kpi"><div class="label">${label}</div><div class="value">${value}</div></div>`)
    .join("");
  renderPeople(data.people || []);
  drawCharts(data.charts || {});
}

async function main() {
  $("refreshBtn").onclick = () => loadCrm();
  $("exportBtn").onclick = () => {
    if (!lastPayload) return;
    const blob = new Blob([JSON.stringify(lastPayload, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `comicengine_crm_${Date.now()}.json`;
    a.click();
  };
  await loadCrm();
  window.addEventListener("resize", () => {
    if (lastPayload) drawCharts(lastPayload.charts || {});
  });
}

main().catch((err) => {
  $("rvMeta").textContent = String(err.message || err);
});
