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
function stars(n) {
  const v = Number(n) || 0;
  return "★".repeat(Math.round(v)) + "☆".repeat(Math.max(0, 5 - Math.round(v)));
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

let peopleCache = [];
let selectedPersonId = null;
let pollTimer = null;

function renderPeople(people) {
  peopleCache = people || [];
  $("peopleMeta").textContent = `${peopleCache.length} people (registered + reviewers)`;
  $("peopleList").innerHTML = peopleCache.length
    ? peopleCache
        .map((p) => {
          const active = p.id === selectedPersonId ? "on" : "";
          return `<button type="button" class="person-chip ${active}" data-id="${esc(p.id)}">
            <strong>${esc(p.name || p.username || "anon")}</strong>
            <span class="muted small">@${esc(p.username || "—")} · logins ${fmt(p.login_count)} · stories ${fmt(p.stories_rated)} · Q ${fmt(p.questionnaire_count || 0)}</span>
          </button>`;
        })
        .join("")
    : `<p class="muted">No readers yet — share the reader URL.</p>`;

  $("peopleList").querySelectorAll(".person-chip").forEach((btn) => {
    btn.onclick = () => {
      selectedPersonId = btn.dataset.id;
      renderPeople(peopleCache);
      showPerson(selectedPersonId);
    };
  });
  if (selectedPersonId) showPerson(selectedPersonId);
  else if (peopleCache[0]) {
    selectedPersonId = peopleCache[0].id;
    renderPeople(peopleCache);
  }
}

function showPerson(id) {
  const p = peopleCache.find((x) => x.id === id);
  if (!p) {
    $("personDetail").innerHTML = `<p class="muted">Select a person.</p>`;
    return;
  }
  const responses = p.responses || [];
  const questionnaires = p.questionnaires || [];
  $("personDetail").innerHTML = `
    <div class="person-head">
      <div>
        <h3>${esc(p.name || p.username)}</h3>
        <p class="muted small">@${esc(p.username || "—")} · joined ${esc((p.created_at || "").slice(0, 10) || "—")} · last login ${esc((p.last_login_at || "").replace("T", " ").slice(0, 19) || "—")}</p>
      </div>
      <div class="person-stats">
        <div><span class="label">Logins</span><strong>${fmt(p.login_count)}</strong></div>
        <div><span class="label">Stories rated</span><strong>${fmt(p.stories_rated)}</strong></div>
        <div><span class="label">Avg overall</span><strong>${p.avg_overall != null ? p.avg_overall + " " + stars(p.avg_overall) : "—"}</strong></div>
        <div><span class="label">Mom Test</span><strong>${fmt(questionnaires.length)}</strong></div>
      </div>
    </div>
    <h3 class="fb-section">Story ratings</h3>
    ${
      responses.length
        ? responses
            .map((item) => {
              const panels = (item.panels || [])
                .map(
                  (pn) => `<li><strong>P${esc(pn.index)}</strong> ${esc(pn.rating)}★ — ${esc(pn.feedback || "—")}</li>`
                )
                .join("");
              return `<article class="fb-card">
                <div class="muted small">${esc((item.created_at || "").replace("T", " ").slice(0, 19))} · ${esc(item.story_id)}</div>
                <p><strong>Overall ${esc(item.overall_rating)}/5</strong> ${stars(item.overall_rating)}</p>
                <p>${esc(item.overall_feedback || "(no written overall feedback)")}</p>
                <ul class="panel-fb">${panels || "<li class='muted'>No panel notes</li>"}</ul>
              </article>`;
            })
            .join("")
        : `<p class="muted">No story ratings yet.</p>`
    }
    <h3 class="fb-section">Mom Test questionnaire</h3>
    ${
      questionnaires.length
        ? questionnaires
            .map((item) => {
              const answers = item.answers || {};
              const rows = Object.entries(answers)
                .map(
                  ([k, v]) =>
                    `<div class="q-ans"><div class="muted small">${esc(k)}</div><p>${esc(v)}</p></div>`
                )
                .join("");
              return `<article class="fb-card">
                <div class="muted small">${esc((item.created_at || "").replace("T", " ").slice(0, 19))} · story ${esc(item.story_id || "—")}</div>
                ${rows || "<p class='muted'>Empty answers</p>"}
              </article>`;
            })
            .join("")
        : `<p class="muted">No Mom Test questionnaire submitted yet.</p>`
    }`;
}

function renderLoginFeed(events) {
  $("loginFeed").innerHTML = (events || []).length
    ? events
        .slice(0, 24)
        .map((ev) => {
          const who = esc(ev.name || ev.username || ev.user_id || "?");
          return `<div class="feed-row"><span class="badge">${esc(ev.action || "login")}</span> <strong>${who}</strong> <span class="muted small">${esc((ev.at || "").replace("T", " ").slice(0, 19))}</span></div>`;
        })
        .join("")
    : `<p class="muted">No login events yet (appear after next register/login).</p>`;
}

function renderFeedbackList(items, source) {
  $("fbMeta").textContent = `${(items || []).length} responses · ${source}`;
  $("feedback").innerHTML = (items || []).length
    ? items
        .slice(0, 20)
        .map((item) => {
          return `<div class="fb-row">
            <div class="muted small">${esc((item.created_at || "").replace("T", " ").slice(0, 19))} · <strong>${esc(item.reviewer_name || item.reviewer_username)}</strong> · ${esc(item.story_id)}</div>
            <p>Overall ${esc(item.overall_rating)}/5 — ${esc((item.overall_feedback || "").slice(0, 160))}</p>
          </div>`;
        })
        .join("")
    : `<p class="muted">No live feedback yet.</p>`;
}

let lastCharts = null;

function drawLiveCharts(charts) {
  lastCharts = charts || lastCharts || {};
  const hist = lastCharts.ratings_hist || [0, 0, 0, 0, 0];
  Charts.bar($("ratingChart"), ["1★", "2★", "3★", "4★", "5★"], hist);
  const days = lastCharts.logins_by_day || [];
  Charts.line(
    $("loginChart"),
    days.map((d) => d.day),
    days.map((d) => d.count)
  );
  const stories = lastCharts.by_story || [];
  Charts.bar(
    $("storyChart"),
    stories.map((s) => String(s.story_id).replace("episode_", "").slice(0, 10)),
    stories.map((s) => s.avg_overall),
    { max: 5 }
  );
}

async function maybeGate() {
  const probe0 = await fetch("/api/gate");
  const gateInfo = await probe0.json().catch(() => ({ password_required: false }));
  if (!gateInfo.password_required) return true;

  if (sessionStorage.getItem("ce_admin_pw")) {
    const probe = await fetch("/api/gate", { headers: authHeaders() });
    if (probe.ok) {
      const ok = await probe.json().catch(() => ({}));
      if (ok.ok) return true;
    }
    sessionStorage.removeItem("ce_admin_pw");
  }

  $("gate").hidden = false;
  $("gateErr").textContent = "";
  $("gatePw").focus();

  return new Promise((resolve) => {
    const submit = async () => {
      const pw = ($("gatePw").value || "").trim();
      if (!pw) {
        $("gateErr").textContent = "Enter the admin password";
        return;
      }
      $("gateErr").textContent = "Checking…";
      $("gateGo").disabled = true;
      sessionStorage.setItem("ce_admin_pw", pw);
      try {
        const probe = await fetch("/api/gate", { headers: authHeaders() });
        const body = await probe.json().catch(() => ({}));
        if (!probe.ok || !body.ok) {
          sessionStorage.removeItem("ce_admin_pw");
          $("gateErr").textContent = body.detail || "Wrong password";
          $("gateGo").disabled = false;
          return;
        }
        $("gate").hidden = true;
        $("gateGo").disabled = false;
        resolve(true);
      } catch (e) {
        $("gateErr").textContent = String(e.message || e);
        $("gateGo").disabled = false;
      }
    };
    $("gateGo").onclick = submit;
    $("gatePw").onkeydown = (ev) => {
      if (ev.key === "Enter") {
        ev.preventDefault();
        submit();
      }
    };
  });
}

async function loadLive() {
  $("livePill").classList.add("pulse");
  const res = await fetch("/api/live-customers", { headers: authHeaders() });
  const data = await res.json().catch(() => ({}));
  $("livePill").classList.remove("pulse");
  if (!res.ok) {
    $("peopleMeta").textContent = data.detail || "live unavailable";
    return;
  }
  const s = data.summary || {};
  $("readerKpis").innerHTML = [
    ["Registered readers", fmt(s.registered_users)],
    ["Feedback responses", fmt(s.feedback_responses)],
    ["Mom Test forms", fmt(s.questionnaire_responses)],
    ["People with ratings", fmt(s.people_with_feedback)],
    ["Live source", esc(data.source || "—")],
  ]
    .map(([label, value]) => `<div class="kpi reader"><div class="label">${label}</div><div class="value">${value}</div></div>`)
    .join("");

  renderPeople(data.people || []);
  renderLoginFeed(data.login_events || []);
  renderFeedbackList(data.feedback || [], data.source || "live");
  drawLiveCharts(data.charts || {});
  $("exportedAt").dataset.liveAt = data.fetched_at || "";
  const snap = $("exportedAt").dataset.snap || "";
  $("exportedAt").textContent = `snapshot ${snap} · live ${esc((data.fetched_at || "").replace("T", " ").slice(0, 19))}`;
}

async function main() {
  await maybeGate();
  const [overview, usage, roi] = await Promise.all([
    loadJson("/data/overview.json"),
    loadJson("/data/usage.json"),
    loadJson("/data/roi.json"),
  ]);

  $("exportedAt").dataset.snap = overview.exported_at || "";
  $("exportedAt").textContent = `snapshot ${overview.exported_at || ""}`;
  if (overview.github) $("ghLink").href = overview.github;

  const t = usage.totals || {};
  $("kpis").innerHTML = [
    ["Engine spend (snapshot)", money(t.cost_usd)],
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

  const unit = roi.unit_economics || {};
  $("roiCards").innerHTML = [
    ["$/story", money(unit.cost_per_story_usd)],
    ["$/panel", money(unit.cost_per_panel_all_in_usd)],
    ["100 eps", money(unit.projected_100_episodes_usd)],
  ]
    .map(([label, value]) => `<div class="unit-card"><div class="label">${label}</div><div class="value">${value}</div></div>`)
    .join("");
  $("roiInsights").innerHTML = (roi.insights || [])
    .slice(0, 6)
    .map((i) => `<li>${esc(i)}</li>`)
    .join("");

  $("refreshLive").onclick = () => loadLive();
  await loadLive();
  clearInterval(pollTimer);
  pollTimer = setInterval(loadLive, 20000);

  // Redraw charts only on resize — do not re-fetch (avoids canvas height compounding)
  let resizeTimer = null;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      if (lastCharts) drawLiveCharts(lastCharts);
    }, 150);
  });
}

main().catch((err) => {
  document.body.insertAdjacentHTML(
    "beforeend",
    `<p class="muted" style="padding:1.5rem">Failed to load admin data: ${esc(err.message)}. Run <code>python scripts/prepare_admin_site.py</code> then redeploy.</p>`
  );
});
