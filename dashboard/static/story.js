const $ = (id) => document.getElementById(id);

function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
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
  document.title = `${ep.title || id} · ComicEngine`;
  $("storyTitle").textContent = ep.title || id;
  $("storyMeta").innerHTML = `
    <p class="muted">${esc(ep.topic || "")}</p>
    <p>${esc(ep.narrative_summary || "")}</p>
    <p class="muted">
      ${esc(data.path || "")} · ${(ep.panels || []).length} panels ·
      <a href="/api/stories/${encodeURIComponent(id)}" target="_blank" rel="noreferrer">raw JSON</a>
    </p>
    ${ep.disclaimer ? `<p class="muted small">${esc(ep.disclaimer)}</p>` : ""}
  `;

  const panels = ep.panels || [];
  $("storyPanels").innerHTML = panels
    .map((p) => {
      const chars = (p.characters || []).join(", ");
      return `<article class="panel-card">
        <div class="panel-idx">Panel ${esc(p.index)}</div>
        <h3>${esc(p.scene_description)}</h3>
        ${p.caption ? `<p class="caption">${esc(p.caption)}</p>` : ""}
        ${p.dialogue ? `<p class="dialogue">“${esc(p.dialogue)}”</p>` : ""}
        <p class="muted small">${esc(chars)} · ${esc(p.emotion || "")}</p>
      </article>`;
    })
    .join("");
}

main();
