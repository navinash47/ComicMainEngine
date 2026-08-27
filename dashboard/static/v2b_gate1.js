const $ = (id) => document.getElementById(id);

function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function countHuman(pairs) {
  return pairs.filter((p) => p.human_winner).length;
}

function render(pairs) {
  const n = pairs.length;
  const done = countHuman(pairs);
  $("progress").textContent = `${done}/${n}`;
  $("status").textContent = done >= n
    ? "All twelve labeled. Agreement will land in the G1 scorecard after the next --agreement run."
    : "Click A, B, or tie under each pair that is ready. Pairs missing a PNG stay skipped until BoN/B1 exists.";
  $("pairs").innerHTML = pairs
    .map((p) => {
      if (!p.ready) {
        return `<article class="v2a-phase">
          <div class="v2a-phase-head"><span class="v2a-id">${esc(p.id)}</span><h3>cam ${esc(p.camera)}</h3>
          <span class="v2a-status locked">waiting</span></div>
          <p class="g1-skip">${esc(p.left)} vs ${esc(p.right)} — PNG not ready yet.</p>
        </article>`;
      }
      const labeled = p.human_winner
        ? `<p class="muted small">You picked ${esc(p.human_winner)}.</p>`
        : "";
      return `<article class="v2a-phase" data-pair="${esc(p.id)}">
        <div class="v2a-phase-head">
          <span class="v2a-id">${esc(p.id)}</span>
          <h3>cam ${esc(p.camera)} · ${esc(p.left)} vs ${esc(p.right)}</h3>
          <span class="v2a-status ${p.human_winner ? "complete" : "in_progress"}">${p.human_winner ? "labeled" : "open"}</span>
        </div>
        <div class="g1-pair">
          <figure><img src="${esc(p.left_url)}" alt="A ${esc(p.left)}" /><figcaption>A · ${esc(p.left)}</figcaption></figure>
          <figure><img src="${esc(p.right_url)}" alt="B ${esc(p.right)}" /><figcaption>B · ${esc(p.right)}</figcaption></figure>
        </div>
        ${labeled}
        <div class="g1-actions">
          <button type="button" class="btn" data-pick="A">A</button>
          <button type="button" class="btn" data-pick="B">B</button>
          <button type="button" class="btn" data-pick="tie">tie</button>
        </div>
      </article>`;
    })
    .join("");
  $("pairs").querySelectorAll("[data-pick]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const article = btn.closest("[data-pair]");
      const pairId = article.getAttribute("data-pair");
      const winner = btn.getAttribute("data-pick");
      const res = await fetch("/api/v2b/preferences", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pair_id: pairId, winner }),
      });
      if (!res.ok) {
        $("status").textContent = `save failed ${res.status}`;
        return;
      }
      load();
    });
  });
}

async function load() {
  const res = await fetch("/api/v2b/gate1/pairs");
  if (!res.ok) {
    $("status").textContent = `Could not load pairs (${res.status}).`;
    return;
  }
  render(await res.json());
}

load();
