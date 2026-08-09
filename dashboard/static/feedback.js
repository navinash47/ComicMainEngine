const $ = (id) => document.getElementById(id);

function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function fieldFor(q) {
  const req = q.required ? "required" : "";
  const hint = q.hint ? `<p class="muted small">${esc(q.hint)}</p>` : "";
  if (q.kind === "choice") {
    const opts = (q.choices || [])
      .map((c) => `<option value="${esc(c)}">${esc(c)}</option>`)
      .join("");
    return `
      <label class="pe-label" for="${esc(q.id)}">${esc(q.prompt)}${q.required ? " *" : ""}</label>
      ${hint}
      <select id="${esc(q.id)}" name="${esc(q.id)}" ${req}>
        <option value="">Select…</option>
        ${opts}
      </select>`;
  }
  if (q.kind === "rating" || q.kind === "nps") {
    const lo = q.min ?? (q.kind === "nps" ? 0 : 1);
    const hi = q.max ?? (q.kind === "nps" ? 10 : 5);
    return `
      <label class="pe-label" for="${esc(q.id)}">${esc(q.prompt)}${q.required ? " *" : ""}</label>
      ${hint}
      <input id="${esc(q.id)}" name="${esc(q.id)}" type="number" min="${lo}" max="${hi}" ${req} />`;
  }
  return `
    <label class="pe-label" for="${esc(q.id)}">${esc(q.prompt)}${q.required ? " *" : ""}</label>
    ${hint}
    <textarea id="${esc(q.id)}" name="${esc(q.id)}" rows="3" ${req} placeholder="Be specific — times, people, what was on screen…"></textarea>`;
}

async function main() {
  await loadAuthChrome();
  const res = await fetch("/api/feedback/questions");
  if (res.status === 401) {
    location.href = "/login?next=/feedback";
    return;
  }
  const data = await res.json();
  $("fbIntro").textContent = data.intro || "";
  const questions = data.questions || [];
  const form = $("fbForm");
  let html = "";
  let section = "";
  questions.forEach((q) => {
    if (q.section && q.section !== section) {
      section = q.section;
      html += `<h2 class="fb-section">${esc(section)}</h2>`;
    }
    html += `<div class="fb-q">${fieldFor(q)}</div>`;
  });
  html += `
    <div class="pe-foot" style="border:0;padding:0;margin-top:1.25rem">
      <button type="submit" class="btn pe-primary">Submit Mom Test feedback</button>
    </div>`;
  form.innerHTML = html;
  form.hidden = false;

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const answers = {};
    questions.forEach((q) => {
      const el = document.getElementById(q.id);
      if (!el) return;
      const v = el.value;
      if (v !== "") answers[q.id] = q.kind === "rating" || q.kind === "nps" ? Number(v) : v;
    });
    $("fbStatus").textContent = "Saving…";
    const post = await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers }),
    });
    const out = await post.json().catch(() => ({}));
    if (!post.ok) {
      $("fbStatus").textContent = out.detail || post.statusText;
      return;
    }
    $("fbStatus").textContent =
      "Thank you — logged for Version 2. You can return to the library.";
    form.hidden = true;
  });
}

main();
