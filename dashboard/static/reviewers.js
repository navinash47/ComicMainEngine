const $ = (id) => document.getElementById(id);

function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function main() {
  const [rev, fb, storyFb] = await Promise.all([
    fetch("/api/reviewers").then((r) => r.json()),
    fetch("/api/feedback/list?limit=50").then((r) => r.json()).catch(() => ({ items: [], summary: {} })),
    fetch("/api/story-feedback?limit=200").then((r) => r.json()),
  ]);

  const rs = rev.summary || {};
  const ss = storyFb.summary || {};
  $("rvMeta").textContent =
    `${rs.reviewers || 0} named people · ${ss.responses || 0} story reviews · Mom Test ${ (fb.summary || {}).responses || 0}`;

  $("reviewerList").innerHTML = (rev.items || [])
    .map(
      (u) => `
      <div class="reviewer-row">
        <strong>${esc(u.name || u.email)}</strong>
        <span class="muted small">${esc(u.email)}${u.is_admin ? " · admin" : ""}</span>
        <span class="muted small">logins ${esc(u.login_count)} · last ${esc(u.last_seen_at)}</span>
      </div>`
    )
    .join("") || `<p class="muted">No register rows yet.</p>`;

  $("feedbackList").innerHTML = (storyFb.items || [])
    .map((item) => {
      const panels = (item.panels || [])
        .map((p) => `P${p.index}:${p.rating}★ ${esc((p.feedback || "").slice(0, 80))}`)
        .join("<br/>");
      return `
        <div class="feedback-row">
          <div class="muted small">${esc(item.created_at)} · <strong>${esc(item.reviewer_name)}</strong> · ${esc(item.story_id)}</div>
          <p>Overall ${esc(item.overall_rating)}/5 — ${esc(item.overall_feedback || "")}</p>
          <details><summary>Panels</summary><p class="muted small">${panels || "—"}</p></details>
        </div>`;
    })
    .join("") || `<p class="muted">No story/panel feedback yet. Send people to /review</p>`;

  $("exportBtn").addEventListener("click", async () => {
    const data = await fetch("/api/story-feedback?limit=2000").then((r) => r.json());
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `story_feedback_${Date.now()}.json`;
    a.click();
  });
}

main();
