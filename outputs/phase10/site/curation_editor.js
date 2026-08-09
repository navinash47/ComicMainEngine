/** Phase 8.5 — panel rate / suggest / edit-prompt editor (Library + Story). */

function escHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function starsHtml(rating, interactive = false, name = "rating") {
  const r = Number(rating) || 0;
  if (!interactive) {
    if (!r) return `<span class="stars muted" title="unrated">☆☆☆☆☆</span>`;
    const filled = "★".repeat(r) + "☆".repeat(5 - r);
    return `<span class="stars" title="${r}/5">${filled}</span>`;
  }
  let html = `<div class="star-picker" data-name="${escHtml(name)}">`;
  for (let i = 1; i <= 5; i += 1) {
    html += `<button type="button" class="star-btn ${i <= r ? "on" : ""}" data-v="${i}" aria-label="${i} stars">★</button>`;
  }
  html += `<span class="star-val muted small">${r ? `${r}/5` : "rate"}</span></div>`;
  return html;
}

function ensureEditorDom() {
  let root = document.getElementById("panelEditor");
  if (root) return root;
  root = document.createElement("div");
  root.id = "panelEditor";
  root.className = "panel-editor-overlay hidden";
  root.innerHTML = `
    <div class="panel-editor" role="dialog" aria-modal="true" aria-labelledby="peTitle">
      <header class="pe-head">
        <div>
          <p class="eyebrow" id="peEyebrow">Panel editor</p>
          <h2 id="peTitle">Edit panel</h2>
        </div>
        <button type="button" class="btn" id="peClose" aria-label="Close">Close</button>
      </header>
      <div class="pe-body">
        <p class="muted small" id="peMeta"></p>
        <label class="pe-label">Human rating (how good for readers)</label>
        <div id="peStars"></div>
        <label class="pe-label" for="peSuggestions">Suggestions for humans / next regen</label>
        <textarea id="peSuggestions" rows="3" placeholder="What should change? face, lighting, composition…"></textarea>
        <label class="pe-label" for="pePrompt">Art prompt (editable)</label>
        <textarea id="pePrompt" rows="6" placeholder="Scene / art direction for this panel"></textarea>
        <label class="pe-label" for="peNote">Note</label>
        <input id="peNote" type="text" placeholder="short curator note" />
        <details class="pe-details">
          <summary>Scene &amp; dialogue (read-only)</summary>
          <p class="muted small" id="peScene"></p>
          <p class="muted small" id="peDialog"></p>
        </details>
        <p class="pe-status muted small" id="peStatus"></p>
      </div>
      <footer class="pe-foot">
        <button type="button" class="btn" id="peSave">Save rating &amp; suggestions</button>
        <button type="button" class="btn pe-danger" id="peReject">Reject + save</button>
        <button type="button" class="btn pe-primary" id="peRegen">Regenerate with this prompt</button>
      </footer>
    </div>`;
  document.body.appendChild(root);
  return root;
}

const PanelEditor = {
  _rating: 0,
  _storyId: "",
  _panel: 0,
  _onDone: null,

  open({ storyId, panel, mode = "edit", onDone = null } = {}) {
    const root = ensureEditorDom();
    this._storyId = storyId;
    this._panel = Number(panel);
    this._onDone = onDone;
    this._mode = mode;
    root.classList.remove("hidden");
    document.getElementById("peTitle").textContent =
      mode === "reject" ? `Reject · Panel ${panel}` : `Edit · Panel ${panel}`;
    document.getElementById("peEyebrow").textContent = storyId;
    document.getElementById("peStatus").textContent = "Loading…";
    this._bindOnce();
    this._load();
  },

  close() {
    const root = document.getElementById("panelEditor");
    if (root) root.classList.add("hidden");
  },

  _bindOnce() {
    if (this._bound) return;
    this._bound = true;
    const root = ensureEditorDom();
    root.addEventListener("click", (ev) => {
      if (ev.target === root) this.close();
    });
    document.getElementById("peClose").addEventListener("click", () => this.close());
    document.getElementById("peSave").addEventListener("click", () => this._save({ status: null }));
    document.getElementById("peReject").addEventListener("click", () =>
      this._save({ status: "rejected", thenRegen: false })
    );
    document.getElementById("peRegen").addEventListener("click", () =>
      this._save({ status: null, thenRegen: true })
    );
    document.getElementById("peStars").addEventListener("click", (ev) => {
      const btn = ev.target.closest(".star-btn");
      if (!btn) return;
      this._rating = Number(btn.dataset.v);
      document.getElementById("peStars").innerHTML = starsHtml(this._rating, true);
    });
  },

  async _load() {
    const res = await fetch(
      `/api/curation/${encodeURIComponent(this._storyId)}/panel/${this._panel}`
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      document.getElementById("peStatus").textContent = data.detail || res.statusText;
      return;
    }
    this._rating = Number(data.rating) || 0;
    document.getElementById("peStars").innerHTML = starsHtml(this._rating, true);
    document.getElementById("peSuggestions").value = data.suggestions || "";
    document.getElementById("pePrompt").value =
      data.prior_prompt || data.art_prompt || data.scene_description || "";
    document.getElementById("peNote").value = data.note || "";
    document.getElementById("peScene").textContent = data.scene_description || "";
    document.getElementById("peDialog").textContent =
      [data.dialogue, data.caption].filter(Boolean).join(" · ") || "(no dialogue)";
    document.getElementById("peMeta").textContent =
      `status ${data.status || "pending"} · chars ${(data.characters || []).join(", ")}`;
    document.getElementById("peStatus").textContent = "";
    if (this._mode === "reject") {
      document.getElementById("peNote").value =
        document.getElementById("peNote").value || "needs regen";
    }
  },

  async _save({ status = null, thenRegen = false } = {}) {
    const suggestions = document.getElementById("peSuggestions").value.trim();
    const prompt = document.getElementById("pePrompt").value.trim();
    const note = document.getElementById("peNote").value.trim();
    const st = document.getElementById("peStatus");
    const rating = this._rating || null;

    try {
      if (thenRegen) {
        st.textContent = "Regenerating image… (API cost)";
        document.getElementById("peRegen").disabled = true;
        const res = await fetch(
          `/api/curation/${encodeURIComponent(this._storyId)}/regenerate`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              panel: this._panel,
              note: note || "ui regenerate with edited prompt",
              prompt,
              rating,
              suggestions,
              mark_rejected_first: this._mode === "reject",
            }),
          }
        );
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || res.statusText);
        st.textContent = `Done · ${data.method || "ok"}`;
        this.close();
        if (this._onDone) await this._onDone({ regenerated: true, data });
        return;
      }

      st.textContent = "Saving…";
      const payload = {
        panel: this._panel,
        note: note || (status === "rejected" ? "rejected" : "rated in editor"),
        rating,
        suggestions,
      };
      if (status) payload.status = status;
      const res = await fetch(`/api/curation/${encodeURIComponent(this._storyId)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || res.statusText);
      st.textContent = "Saved";
      this.close();
      if (this._onDone) await this._onDone({ regenerated: false, data });
    } catch (err) {
      st.textContent = String(err.message || err);
    } finally {
      document.getElementById("peRegen").disabled = false;
    }
  },
};

window.PanelEditor = PanelEditor;
window.starsHtml = starsHtml;
window.escHtml = escHtml;
