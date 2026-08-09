/** Public review — comics + panel/story ratings + Mom Test (local FastAPI). */

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
      .map((s, i) => {
        const thumb = s.thumbnail_href || (s.panels && s.panels[0] && s.panels[0].image_href) || "";
        return `<article class="comic-card" style="--delay:${i * 60}ms">
          <a class="comic-thumb-link" href="/review/${encodeURIComponent(s.id)}?mode=rate">
            ${
              thumb
                ? `<img class="comic-thumb" src="${esc(thumb)}" alt="" loading="lazy" />`
                : `<div class="comic-thumb" style="display:flex;align-items:center;justify-content:center;color:var(--muted)">No preview</div>`
            }
          </a>
          <div class="comic-body">
            <p class="eyebrow">${esc(s.panel_count)} panels</p>
            <h2 class="comic-title">${esc(s.title)}</h2>
            <p class="muted comic-topic">${esc(s.topic)}</p>
            <div class="comic-actions">
              <a class="btn pe-primary" href="/review/${encodeURIComponent(s.id)}?mode=rate">Read &amp; rate</a>
              ${s.pdf_href ? `<a class="btn" href="${esc(s.pdf_href)}" target="_blank" rel="noopener">PDF</a>` : ""}
              <a class="btn" href="/review/${encodeURIComponent(s.id)}?mode=read">Just read</a>
            </div>
          </div>
        </article>`;
      })
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
    const parts = location.pathname.split("/").filter(Boolean);
    const id = decodeURIComponent(parts[parts.length - 1] || "");
    const mode = (new URLSearchParams(location.search).get("mode") || "rate").toLowerCase();
    const readOnly = mode === "read" || mode === "just" || mode === "readonly";

    const res = await fetch("/api/public/stories");
    const data = await res.json();
    const story = (data.stories || []).find((s) => s.id === id);
    if (!story) {
      document.getElementById("storyTitle").textContent = "Story not found";
      return;
    }
    document.getElementById("storyTitle").textContent = story.title;
    document.getElementById("storyTopic").textContent = story.topic || "";
    document.getElementById("editionLinks").innerHTML = `
      <a class="btn pe-primary" href="/review/${encodeURIComponent(story.id)}?mode=rate">Read &amp; rate</a>
      ${story.pdf_href ? `<a class="btn" href="${esc(story.pdf_href)}" target="_blank" rel="noopener">PDF</a>` : ""}
      <a class="btn" href="/review/${encodeURIComponent(story.id)}?mode=read">Just read</a>`;

    if (readOnly) {
      document.getElementById("modePill").hidden = false;
      document.getElementById("overallBox").hidden = true;
    }

    document.getElementById("panels").innerHTML = (story.panels || [])
      .map((p) => {
        const img = p.image_href
          ? `<img class="panel-img" src="${esc(p.image_href)}" alt="Panel ${esc(p.index)}" loading="lazy" />`
          : `<p class="muted">No image</p>`;
        const rateBlock = readOnly
          ? ""
          : `<div class="panel-curation">
            <label class="pe-label">Your rating for this panel</label>
            ${starsSelect(`p-rate-${p.index}`, true)}
            <label class="pe-label" for="p-fb-${p.index}">Panel feedback</label>
            <textarea id="p-fb-${p.index}" rows="2" placeholder="What was good / confusing / broken here?"></textarea>
          </div>`;
        return `<article class="panel-card" data-panel="${esc(p.index)}">
          <div class="panel-idx">Panel ${esc(p.index)}</div>
          <h3>${esc(p.scene_description)}</h3>
          ${img}
          ${p.dialogue ? `<p class="dialogue">${esc(p.dialogue)}</p>` : ""}
          ${p.caption ? `<p class="caption">${esc(p.caption)}</p>` : ""}
          ${rateBlock}
        </article>`;
      })
      .join("");

    if (readOnly) return;

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
      document.getElementById("submitStatus").textContent = "Saved — opening questionnaire…";
      document.getElementById("submitAll").disabled = true;
      setTimeout(() => {
        location.href = `/review/questionnaire?story=${encodeURIComponent(story.id)}`;
      }, 500);
    };
  },
};

const ReviewQuestionnaire = {
  async init() {
    const name = ReviewStore.getName();
    if (!name) {
      location.href = "/review";
      return;
    }
    document.getElementById("whoHint").textContent = `as ${name}`;
    const storyId = new URLSearchParams(location.search).get("story") || "";
    const res = await fetch("/api/public/questionnaire");
    if (!res.ok) {
      document.getElementById("intro").textContent = "Could not load questions.";
      return;
    }
    const meta = await res.json();
    document.getElementById("intro").textContent = meta.intro || "";
    document.getElementById("storyHint").textContent = storyId
      ? `Linked to the story you just rated: ${storyId}`
      : "A few questions about your real habits and this session.";

    const form = document.getElementById("qForm");
    form.hidden = false;
    let lastSection = "";
    const bits = [];
    for (const q of meta.questions || []) {
      if (q.section && q.section !== lastSection) {
        lastSection = q.section;
        bits.push(`<h2 class="fb-section">${esc(q.section)}</h2>`);
      }
      bits.push(`<div class="fb-q">`);
      bits.push(`<label class="pe-label" for="ans-${esc(q.id)}">${esc(q.prompt)}${q.required ? " *" : ""}</label>`);
      if (q.hint) bits.push(`<p class="muted small">${esc(q.hint)}</p>`);
      if (q.kind === "choice") {
        bits.push(`<select id="ans-${esc(q.id)}" ${q.required ? "required" : ""}>`);
        bits.push(`<option value="">Select…</option>`);
        for (const c of q.choices || []) bits.push(`<option value="${esc(c)}">${esc(c)}</option>`);
        bits.push(`</select>`);
      } else {
        bits.push(
          `<textarea id="ans-${esc(q.id)}" rows="3" ${q.required ? "required" : ""} placeholder="Write a concrete answer…"></textarea>`
        );
      }
      bits.push(`</div>`);
    }
    bits.push(`<div class="pe-foot" style="border:0;margin-top:1.25rem">
      <button type="submit" class="btn pe-primary">Submit questionnaire</button>
      <a class="btn" href="/review">Skip to stories</a>
    </div>`);
    form.innerHTML = bits.join("");

    form.onsubmit = async (ev) => {
      ev.preventDefault();
      const answers = {};
      for (const q of meta.questions || []) {
        const el = document.getElementById(`ans-${q.id}`);
        const val = (el && el.value ? el.value : "").trim();
        if (q.required && !val) {
          document.getElementById("qStatus").textContent = `Please answer: ${q.prompt}`;
          el && el.focus();
          return;
        }
        if (val) answers[q.id] = val;
      }
      document.getElementById("qStatus").textContent = "Saving…";
      const post = await fetch("/api/public/questionnaire", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, story_id: storyId, answers }),
      });
      const out = await post.json().catch(() => ({}));
      if (!post.ok) {
        document.getElementById("qStatus").textContent = out.detail || "Save failed";
        return;
      }
      document.getElementById("qStatus").textContent = "Saved — thank you.";
      form.querySelector('button[type="submit"]').disabled = true;
      setTimeout(() => {
        location.href = "/review";
      }, 1000);
    };
  },
};

window.ReviewHome = ReviewHome;
window.ReviewStory = ReviewStory;
window.ReviewQuestionnaire = ReviewQuestionnaire;
window.ReviewStore = ReviewStore;
