/** Public review — comics + panel/story ratings only (no stats). */

const ReviewStore = {
  getName() {
    return (localStorage.getItem("ce_review_name") || "").trim();
  },
  setName(name) {
    localStorage.setItem("ce_review_name", name.trim());
  },
};

function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function starsSelect(id, required = false) {
  return `<select id="${esc(id)}" ${required ? "required" : ""}>
    <option value="">Rate…</option>
    <option value="1">1 ★</option>
    <option value="2">2 ★★</option>
    <option value="3">3 ★★★</option>
    <option value="4">4 ★★★★</option>
    <option value="5">5 ★★★★★</option>
  </select>`;
}

const ReviewHome = {
  async init() {
    const input = document.getElementById("displayName");
    const existing = ReviewStore.getName();
    if (existing) {
      input.value = existing;
      document.getElementById("whoHint").textContent = `Reviewing as ${existing}`;
      document.getElementById("nameStatus").textContent = "Name saved on this device.";
    }
    document.getElementById("saveName").onclick = async () => {
      const name = input.value.trim();
      if (!name) {
        document.getElementById("nameStatus").textContent = "Please enter a name.";
        return;
      }
      ReviewStore.setName(name);
      await fetch("/api/public/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      }).catch(() => ({}));
      document.getElementById("whoHint").textContent = `Reviewing as ${name}`;
      document.getElementById("nameStatus").textContent = "Saved. Pick a story below.";
    };

    const res = await fetch("/api/public/stories");
    const data = await res.json();
    const grid = document.getElementById("storyGrid");
    grid.innerHTML = (data.stories || [])
      .map(
        (s) => `<article class="library-card">
          <p class="eyebrow">${esc(s.panel_count)} panels</p>
          <h2>${esc(s.title)}</h2>
          <p class="muted">${esc(s.topic)}</p>
          <div class="link-row" style="margin-top:0.75rem">
            <a class="btn pe-primary" href="/review/${encodeURIComponent(s.id)}">Read &amp; rate</a>
            ${s.pdf_href ? `<a class="btn" href="${esc(s.pdf_href)}" target="_blank" rel="noopener">PDF</a>` : ""}
          </div>
        </article>`
      )
      .join("") || `<p class="muted" style="padding:0 2rem">No stories yet.</p>`;
  },
};

const ReviewStory = {
  async init() {
    const name = ReviewStore.getName();
    if (!name) {
      location.href = "/review";
      return;
    }
    document.getElementById("whoHint").textContent = `as ${name}`;
    const id = decodeURIComponent(location.pathname.split("/").filter(Boolean).pop() || "");
    const res = await fetch("/api/public/stories");
    const data = await res.json();
    const story = (data.stories || []).find((s) => s.id === id);
    if (!story) {
      document.getElementById("storyTitle").textContent = "Story not found";
      return;
    }
    document.getElementById("storyTitle").textContent = story.title;
    document.getElementById("storyTopic").textContent = story.topic || "";
    document.getElementById("editionLinks").innerHTML = [
      story.webtoon_href
        ? `<a class="btn" href="${esc(story.webtoon_href)}" target="_blank" rel="noopener">Full webtoon</a>`
        : "",
      story.pdf_href
        ? `<a class="btn" href="${esc(story.pdf_href)}" target="_blank" rel="noopener">PDF</a>`
        : "",
    ].join("");

    const panelsEl = document.getElementById("panels");
    panelsEl.innerHTML = (story.panels || [])
      .map((p) => {
        const img = p.image_href
          ? `<img class="panel-img" src="${esc(p.image_href)}" alt="Panel ${esc(p.index)}" loading="lazy" />`
          : `<p class="muted">No image</p>`;
        return `<article class="panel-card" data-panel="${esc(p.index)}">
          <div class="panel-idx">Panel ${esc(p.index)}</div>
          <h3>${esc(p.scene_description)}</h3>
          ${img}
          ${p.dialogue ? `<p class="dialogue">${esc(p.dialogue)}</p>` : ""}
          ${p.caption ? `<p class="caption">${esc(p.caption)}</p>` : ""}
          <div class="panel-curation">
            <label class="pe-label">Your rating for this panel</label>
            ${starsSelect(`p-rate-${p.index}`, true)}
            <label class="pe-label" for="p-fb-${p.index}">Panel feedback</label>
            <textarea id="p-fb-${p.index}" rows="2" placeholder="What was good / confusing / broken here?"></textarea>
          </div>
        </article>`;
      })
      .join("");

    document.getElementById("submitAll").onclick = async () => {
      const overall = Number(document.getElementById("overallRating").value);
      const overallFb = document.getElementById("overallFeedback").value.trim();
      if (!overall) {
        document.getElementById("submitStatus").textContent = "Pick an overall rating.";
        return;
      }
      const panels = [];
      for (const p of story.panels || []) {
        const rateEl = document.getElementById(`p-rate-${p.index}`);
        const fbEl = document.getElementById(`p-fb-${p.index}`);
        const rating = Number(rateEl && rateEl.value);
        if (!rating) {
          document.getElementById("submitStatus").textContent = `Rate panel ${p.index} before submitting.`;
          return;
        }
        panels.push({
          index: p.index,
          rating,
          feedback: (fbEl && fbEl.value.trim()) || "",
        });
      }
      document.getElementById("submitStatus").textContent = "Submitting…";
      const post = await fetch("/api/public/story-feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          story_id: story.id,
          overall_rating: overall,
          overall_feedback: overallFb,
          panels,
        }),
      });
      const out = await post.json().catch(() => ({}));
      if (!post.ok) {
        document.getElementById("submitStatus").textContent = out.detail || post.statusText;
        return;
      }
      document.getElementById("submitStatus").textContent = "Thank you — feedback saved.";
      document.getElementById("submitAll").disabled = true;
    };
  },
};

window.ReviewHome = ReviewHome;
window.ReviewStory = ReviewStory;
window.ReviewStore = ReviewStore;
