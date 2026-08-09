const $ = (id) => document.getElementById(id);

function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function editionBlock(title, ed) {
  if (!ed) return "";
  const avail = ed.available;
  return `
    <div class="edition-card ${avail ? "" : "dim"}">
      <h3>${esc(title)}</h3>
      <p class="muted small">${esc(ed.label || "")} · ${esc(ed.phase || "")}</p>
      <div class="link-row">
        ${ed.webtoon_href && avail ? `<a class="btn" href="${esc(ed.webtoon_href)}" target="_blank" rel="noopener">Webtoon</a>` : ""}
        ${ed.pdf_href && avail ? `<a class="btn" href="${esc(ed.pdf_href)}" target="_blank" rel="noopener">PDF</a>` : ""}
        ${!avail ? `<span class="muted small">Not assembled</span>` : ""}
      </div>
      ${ed.webtoon_href && avail
        ? `<img class="webtoon-preview" src="${esc(ed.webtoon_href)}" alt="${esc(title)}" loading="lazy" />`
        : ""}
    </div>`;
}

function chipLabel(p) {
  const st = p.status || "pending";
  const stars = p.rating ? ` · ${"★".repeat(p.rating)}${"☆".repeat(5 - p.rating)}` : "";
  return `P${p.index} · ${st}${stars}`;
}

function curationBlock(story) {
  const c = story.curation || {};
  const panels = (c.panels || []).slice().sort((a, b) => (a.index || 0) - (b.index || 0));
  const avg = c.avg_rating != null ? ` · avg ${c.avg_rating}/5` : "";
  const chips = panels
    .map((p) => {
      const st = p.status || "pending";
      const tip = [p.note, p.suggestions].filter(Boolean).join(" — ") || st;
      return `<button type="button" class="curation-chip status-${esc(st)}" data-story="${esc(story.id)}" data-panel="${esc(p.index)}" title="${esc(tip)}">${esc(chipLabel(p))}</button>`;
    })
    .join("");
  return `
    <div class="curation-block">
      <div class="curation-head">
        <h3>Curation · Phase 8.5</h3>
        <p class="muted small">
          episode: <strong>${esc(c.episode_status || "pending")}</strong>
          · approved ${esc(c.approved || 0)}
          · rejected ${esc(c.rejected || 0)}
          · pending ${esc(c.pending || 0)}
          · regen ${esc(c.regenerated || 0)}${esc(avg)}
        </p>
      </div>
      <div class="link-row">
        <button type="button" class="btn act-approve-ep" data-story="${esc(story.id)}">Approve episode</button>
        <button type="button" class="btn act-reject-ep" data-story="${esc(story.id)}">Reject episode</button>
      </div>
      <div class="curation-chips">${chips || '<span class="muted small">No panel rows — click Seed.</span>'}</div>
      <p class="muted small">Click chip = rate / edit prompt · Shift = reject editor · Alt = approve quickly.</p>
    </div>`;
}

async function patchCuration(storyId, body) {
  const res = await fetch(`/api/curation/${encodeURIComponent(storyId)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function openPanelEditor(storyId, panel, mode = "edit") {
  PanelEditor.open({
    storyId,
    panel,
    mode,
    onDone: async () => {
      await loadLibrary(true);
    },
  });
}

function bindCurationActions() {
  document.querySelectorAll(".act-approve-ep").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await patchCuration(btn.dataset.story, { status: "approved", note: "episode approved in library" });
      await loadLibrary(true);
    });
  });
  document.querySelectorAll(".act-reject-ep").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const note = prompt("Reject episode — why?", "needs work") || "rejected";
      await patchCuration(btn.dataset.story, { status: "rejected", note });
      await loadLibrary(true);
    });
  });
  document.querySelectorAll(".curation-chip").forEach((btn) => {
    btn.addEventListener("click", async (ev) => {
      const story = btn.dataset.story;
      const panel = Number(btn.dataset.panel);
      try {
        if (ev.altKey) {
          await patchCuration(story, { status: "approved", panel, note: "approved in library" });
          await loadLibrary(true);
        } else if (ev.shiftKey) {
          openPanelEditor(story, panel, "reject");
        } else {
          openPanelEditor(story, panel, "edit");
        }
      } catch (err) {
        alert(String(err.message || err));
        await loadLibrary(true);
      }
    });
  });
}

async function loadLibrary(refresh = false) {
  const url = refresh ? "/api/library?refresh=true" : "/api/library";
  const res = await fetch(url);
  const data = await res.json();
  $("updated").textContent = data.updated_at
    ? `updated ${new Date(data.updated_at).toLocaleString()}`
    : "ready";
  const cs = data.curation_summary || {};
  const by = (cs.by_status || []).map((x) => `${x.status}:${x.n}`).join(" · ");
  $("libMeta").textContent = `${data.count || 0} stories · store ${data.store_path || "outputs/library/catalog.json"}${by ? ` · curation ${by}` : ""}`;

  const stories = data.stories || [];
  if (!stories.length) {
    $("libraryGrid").innerHTML = `<p class="muted" style="padding:0 2rem">No stories in library yet.</p>`;
    return;
  }

  $("libraryGrid").innerHTML = stories
    .map((s) => {
      const eds = s.editions || {};
      return `
        <article class="library-card">
          <div class="library-head">
            <div>
              <p class="eyebrow">${esc(s.phase)} · ${esc(s.panel_count)} panels</p>
              <h2>${esc(s.title)}</h2>
              <p class="muted">${esc(s.topic)}</p>
            </div>
            <div class="link-row">
              <a class="btn" href="${esc(s.reader_href)}">Open reader</a>
              <a class="btn" href="${esc(s.json_href)}" target="_blank" rel="noreferrer">JSON</a>
            </div>
          </div>
          ${curationBlock(s)}
          <div class="edition-grid">
            ${editionBlock("Reader edition", eds.reader)}
            ${editionBlock("Only Image", eds.image_only)}
          </div>
        </article>`;
    })
    .join("");
  bindCurationActions();
}

$("refreshLib").addEventListener("click", async () => {
  $("updated").textContent = "refreshing…";
  await fetch("/api/library/refresh", { method: "POST" });
  await loadLibrary(true);
});

$("seedCurate").addEventListener("click", async () => {
  $("updated").textContent = "seeding…";
  await fetch("/api/curation/seed", { method: "POST" });
  await loadLibrary(true);
});

loadLibrary();
loadAuthChrome();
