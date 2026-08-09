const $ = (id) => document.getElementById(id);

function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function nl2br(s) {
  return esc(s).replaceAll("\n", "<br/>");
}

function mediaHref(path) {
  if (!path) return "";
  const s = String(path).replaceAll("\\", "/");
  const rel = s.startsWith("outputs/") ? s.slice("outputs/".length) : s;
  return `/media/${rel}`;
}

function curationBar(storyId, panel) {
  const c = panel.curation || {};
  const st = c.status || "pending";
  const rating = c.rating || 0;
  const stars = rating
    ? "★".repeat(rating) + "☆".repeat(5 - rating)
    : "☆☆☆☆☆";
  const tip = c.suggestions || c.note || "Rate / edit / regenerate";
  return `
    <div class="panel-curation">
      <span class="curation-pill status-${esc(st)}" title="${esc(tip)}">${esc(st)} · ${esc(stars)}</span>
      ${c.suggestions ? `<p class="suggest-line muted small">${esc(c.suggestions)}</p>` : ""}
      <div class="link-row panel-curation-actions">
        <button type="button" class="btn act-panel-edit" data-story="${esc(storyId)}" data-panel="${esc(panel.index)}">Rate &amp; edit prompt</button>
        <button type="button" class="btn act-panel-reject" data-story="${esc(storyId)}" data-panel="${esc(panel.index)}">Reject…</button>
        <button type="button" class="btn act-panel-approve" data-story="${esc(storyId)}" data-panel="${esc(panel.index)}">Approve</button>
      </div>
    </div>`;
}

function bindPanelCuration(storyId) {
  const refresh = async () => {
    await main();
  };
  document.querySelectorAll(".act-panel-edit").forEach((btn) => {
    btn.addEventListener("click", () => {
      PanelEditor.open({
        storyId: btn.dataset.story,
        panel: Number(btn.dataset.panel),
        mode: "edit",
        onDone: refresh,
      });
    });
  });
  document.querySelectorAll(".act-panel-reject").forEach((btn) => {
    btn.addEventListener("click", () => {
      PanelEditor.open({
        storyId: btn.dataset.story,
        panel: Number(btn.dataset.panel),
        mode: "reject",
        onDone: refresh,
      });
    });
  });
  document.querySelectorAll(".act-panel-approve").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await fetch(`/api/curation/${encodeURIComponent(btn.dataset.story)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status: "approved",
          panel: Number(btn.dataset.panel),
          note: "approved in reader",
        }),
      });
      await refresh();
    });
  });
}

async function main() {
  const id = decodeURIComponent(location.pathname.split("/").filter(Boolean).pop() || "");
  const res = await fetch(`/api/stories/${encodeURIComponent(id)}`);
  if (!res.ok) {
    $("storyTitle").textContent = "Story not found";
    $("storyMeta").innerHTML = `<p class="muted">No episode JSON for <code>${esc(id)}</code>.</p>`;
    return;
  }
  const data = await res.json();
  const ep = data.episode || {};
  const bridges = data.bridges || [];
  const bridgeByPanel = new Map(
    bridges.map((b) => [Number(b.before_panel), b.text || ""])
  );

  document.title = `${ep.title || id} · ComicEngine`;
  $("storyTitle").textContent = ep.title || id;
  $("storyMeta").innerHTML = `
    <p class="eyebrow">${esc(ep.voice || "story")} · ${esc(ep.topic || "")}</p>
    <p class="lede">${esc(ep.narrative_summary || "")}</p>
    <p class="muted">
      ${esc(data.path || "")} · ${(ep.panels || []).length} panels ·
      <a href="/api/stories/${encodeURIComponent(id)}" target="_blank" rel="noreferrer">raw JSON</a>
    </p>
    ${ep.disclaimer ? `<p class="muted small">${esc(ep.disclaimer)}</p>` : ""}
  `;

  const assembly = data.assembly || {};
  const assemblyOnly = data.assembly_image_only || {};
  if (assembly.webtoon_href || assembly.pdf_href || assemblyOnly.webtoon_href || assemblyOnly.pdf_href) {
    $("storyMeta").innerHTML += `
      <div class="assembly-links">
        <h2>Full episode editions</h2>
        <p class="muted small">Stored in Story Library · Phase 7 Reader vs Phase 7.5 Only Image.</p>
        <div class="edition-grid">
          <div class="edition-card">
            <h3>Reader edition</h3>
            <p class="muted small">Bubbles + captions (Phase 7)</p>
            <div class="link-row">
              ${assembly.webtoon_href ? `<a class="btn" href="${esc(assembly.webtoon_href)}" target="_blank" rel="noopener">Webtoon</a>` : ""}
              ${assembly.pdf_href ? `<a class="btn" href="${esc(assembly.pdf_href)}" target="_blank" rel="noopener">PDF</a>` : ""}
            </div>
            ${assembly.webtoon_href ? `<img class="webtoon-preview" src="${esc(assembly.webtoon_href)}" alt="Reader webtoon" loading="lazy" />` : `<p class="muted">Not assembled yet.</p>`}
          </div>
          <div class="edition-card">
            <h3>Only Image</h3>
            <p class="muted small">Raw panels, no bubbles (Phase 7.5)</p>
            <div class="link-row">
              ${assemblyOnly.webtoon_href ? `<a class="btn" href="${esc(assemblyOnly.webtoon_href)}" target="_blank" rel="noopener">Webtoon</a>` : ""}
              ${assemblyOnly.pdf_href ? `<a class="btn" href="${esc(assemblyOnly.pdf_href)}" target="_blank" rel="noopener">PDF</a>` : ""}
            </div>
            ${assemblyOnly.webtoon_href ? `<img class="webtoon-preview" src="${esc(assemblyOnly.webtoon_href)}" alt="Only Image webtoon" loading="lazy" />` : `<p class="muted">Not assembled yet.</p>`}
          </div>
        </div>
        <p><a class="btn" href="/library">Open Story Library →</a></p>
      </div>`;
  }

  const cast = (ep.characters || [])
    .slice(0, 12)
    .map((c) => `<li><strong>${esc(c.display_name)}</strong> — ${esc(c.role || "")}</li>`)
    .join("");
  if (cast) {
    $("storyMeta").innerHTML += `
      <div class="cast-block">
        <h2>Who's speaking</h2>
        <ul class="cast-list">${cast}</ul>
      </div>`;
  }

  const fact = (ep.fact_sheet || [])
    .slice(0, 6)
    .map((f) => `<li>${esc(f)}</li>`)
    .join("");
  if (fact) {
    $("storyMeta").innerHTML += `
      <div class="facts-block">
        <h2>Before you scroll</h2>
        <ul>${fact}</ul>
      </div>`;
  }

  const panels = ep.panels || [];
  const chunks = [];
  panels.forEach((p, idx) => {
    const bridge = bridgeByPanel.get(Number(p.index));
    if (bridge) {
      chunks.push(`
        <div class="story-bridge">
          <p class="bridge-label">${idx === 0 ? "Opening" : "Meanwhile"}</p>
          <p>${nl2br(bridge)}</p>
        </div>`);
    }

    const chars = (p.characters || []).join(", ");
    const imgHref = p.image_href || mediaHref(p.composed_image_path || p.image_path);
    const kind = p.image_kind || (p.composed_image_path ? "composed" : "raw");
    const img = imgHref
      ? `<img class="panel-img" data-panel-img="${esc(p.index)}" src="${esc(imgHref)}" alt="Panel ${esc(p.index)}" loading="lazy" />`
      : `<p class="muted">No panel image yet.</p>`;

    chunks.push(`
      <article class="panel-card" data-panel="${esc(p.index)}">
        <div class="panel-idx">Panel ${esc(p.index)} · ${esc(kind)}</div>
        <h3>${esc(p.scene_description)}</h3>
        ${img}
        ${curationBar(id, p)}
        ${p.dialogue ? `<div class="dialogue-block"><p class="dialogue-label">Dialogue</p><p class="dialogue">${nl2br(p.dialogue)}</p></div>` : ""}
        ${p.caption ? `<p class="caption"><span class="caption-label">Caption</span> ${esc(p.caption)}</p>` : ""}
        <p class="muted small">${esc(chars)}${p.emotion ? ` · ${esc(p.emotion)}` : ""}${p.image_method ? ` · render: ${esc(p.image_method)}` : ""}</p>
      </article>`);
  });

  if ((ep.fact_checks || []).length) {
    chunks.push(`
      <section class="facts-block closing-notes">
        <h2>Fact checks</h2>
        <ul>
          ${(ep.fact_checks || []).map((f) =>
            `<li><strong>${esc(f.verdict)}</strong> — ${esc(f.claim)}${f.source_note ? ` <span class="muted">(${esc(f.source_note)})</span>` : ""}</li>`
          ).join("")}
        </ul>
      </section>`);
  }

  $("storyPanels").innerHTML = chunks.join("") + `
    <section class="facts-block closing-notes">
      <h2>Mom Test feedback</h2>
      <p class="muted">When you’re done reading: what happened in your world, and what happened on screen — not compliments.</p>
      <p><a class="btn pe-primary" href="/feedback">Open feedback questionnaire →</a></p>
    </section>`;
  bindPanelCuration(id);
  if (window.loadAuthChrome) loadAuthChrome();
}

main();
