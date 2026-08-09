const Auth = {
  tokenKey: "ce_reader_token",
  userKey: "ce_reader_user",
  getToken() {
    return localStorage.getItem(this.tokenKey) || "";
  },
  getUser() {
    try {
      return JSON.parse(localStorage.getItem(this.userKey) || "null");
    } catch {
      return null;
    }
  },
  setSession(token, user) {
    if (token) localStorage.setItem(this.tokenKey, token);
    if (user) localStorage.setItem(this.userKey, JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
  },
  headers(json = true) {
    const h = {};
    if (json) h["Content-Type"] = "application/json";
    const t = this.getToken();
    if (t) {
      h.Authorization = `Bearer ${t}`;
      h["x-session-token"] = t;
    }
    return h;
  },
  async requireLogin() {
    const token = this.getToken();
    const cached = this.getUser();
    if (!token && !cached) {
      location.replace("/login.html");
      return null;
    }
    try {
      const res = await fetch("/api/auth/me", {
        headers: this.headers(false),
        credentials: "include",
        cache: "no-store",
      });
      const data = await res.json().catch(() => null);
      if (data && data.authenticated && data.user) {
        this.setSession(token || this.getToken(), data.user);
        return data.user;
      }
      if (data && data.authenticated === false) {
        this.clear();
        location.replace("/login.html");
        return null;
      }
      if (cached) return cached;
    } catch {
      if (cached) return cached;
    }
    this.clear();
    location.replace("/login.html");
    return null;
  },
};

function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function rateSelect(id) {
  return `<select id="${esc(id)}">
    <option value="">Rate…</option>
    <option value="1">1 ★</option>
    <option value="2">2 ★★</option>
    <option value="3">3 ★★★</option>
    <option value="4">4 ★★★★</option>
    <option value="5">5 ★★★★★</option>
  </select>`;
}

async function loadStories() {
  const res = await fetch("/stories.json");
  if (!res.ok) throw new Error("stories.json missing — run prepare_feedback_beta.py before deploy");
  return res.json();
}

const AuthPage = {
  init() {
    const loginForm = document.getElementById("loginForm");
    const registerForm = document.getElementById("registerForm");
    document.getElementById("tabLogin").onclick = () => {
      loginForm.hidden = false;
      registerForm.hidden = true;
    };
    document.getElementById("tabRegister").onclick = () => {
      loginForm.hidden = true;
      registerForm.hidden = false;
    };

    (async () => {
      if (!Auth.getToken() && !Auth.getUser()) return;
      try {
        const res = await fetch("/api/auth/me", {
          headers: Auth.headers(false),
          credentials: "include",
          cache: "no-store",
        });
        const data = await res.json().catch(() => null);
        if (data && data.authenticated) location.replace("/");
      } catch {
        /* stay */
      }
    })();

    loginForm.onsubmit = async (ev) => {
      ev.preventDefault();
      document.getElementById("authStatus").textContent = "Signing in…";
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          username: document.getElementById("loginUsername").value,
          password: document.getElementById("loginPassword").value,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        document.getElementById("authStatus").textContent = data.detail || "Login failed";
        return;
      }
      Auth.setSession(data.token, data.user);
      location.replace("/");
    };
    registerForm.onsubmit = async (ev) => {
      ev.preventDefault();
      document.getElementById("authStatus").textContent = "Creating account…";
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          username: document.getElementById("regUsername").value,
          name: document.getElementById("regName").value,
          password: document.getElementById("regPassword").value,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        document.getElementById("authStatus").textContent = data.detail || "Register failed";
        return;
      }
      Auth.setSession(data.token, data.user);
      location.replace("/");
    };
  },
};

const Home = {
  async init() {
    const user = await Auth.requireLogin();
    if (!user) return;
    document.getElementById("whoHint").textContent = user.name || user.username;
    document.getElementById("authLink").hidden = true;
    document.getElementById("logoutBtn").hidden = false;
    document.getElementById("logoutBtn").onclick = async () => {
      await fetch("/api/auth/logout", {
        method: "POST",
        headers: Auth.headers(),
        credentials: "include",
      });
      Auth.clear();
      location.replace("/login.html");
    };
    const data = await loadStories();
    const grid = document.getElementById("storyGrid");
    grid.innerHTML = (data.stories || [])
      .map((s, i) => {
        const thumb = s.thumbnail || (s.panels && s.panels[0] && s.panels[0].image) || s.webtoon;
        return `<article class="comic-card" style="--delay:${i * 60}ms">
          <a class="comic-thumb-link" href="/story.html?id=${encodeURIComponent(s.id)}&mode=rate">
            <img class="comic-thumb" src="${esc(thumb)}" alt="" loading="lazy" />
          </a>
          <div class="comic-body">
            <p class="eyebrow">${esc(s.panel_count)} panels</p>
            <h2 class="comic-title">${esc(s.title)}</h2>
            <p class="muted comic-topic">${esc(s.topic)}</p>
            <div class="comic-actions">
              <a class="btn pe-primary" href="/story.html?id=${encodeURIComponent(s.id)}&mode=rate">Read &amp; rate</a>
              <a class="btn" href="${esc(s.pdf)}" target="_blank" rel="noopener">PDF</a>
              <a class="btn" href="/story.html?id=${encodeURIComponent(s.id)}&mode=read">Just read</a>
            </div>
          </div>
        </article>`;
      })
      .join("");
  },
};

const StoryPage = {
  async init() {
    const user = await Auth.requireLogin();
    if (!user) return;
    document.getElementById("whoHint").textContent = user.name || user.username;
    const params = new URLSearchParams(location.search);
    const id = params.get("id");
    const mode = (params.get("mode") || "rate").toLowerCase();
    const readOnly = mode === "read" || mode === "just" || mode === "readonly";

    const data = await loadStories();
    const story = (data.stories || []).find((s) => s.id === id);
    if (!story) {
      document.getElementById("storyTitle").textContent = "Not found";
      return;
    }
    document.getElementById("storyTitle").textContent = story.title;
    document.getElementById("storyTopic").textContent = story.topic || "";
    document.getElementById("editionLinks").innerHTML = `
      <a class="btn pe-primary" href="/story.html?id=${encodeURIComponent(story.id)}&mode=rate">Read &amp; rate</a>
      <a class="btn" href="${esc(story.pdf)}" target="_blank" rel="noopener">PDF</a>
      <a class="btn" href="/story.html?id=${encodeURIComponent(story.id)}&mode=read">Just read</a>`;

    if (readOnly) {
      document.getElementById("modePill").hidden = false;
      document.getElementById("feedbackForm").hidden = true;
    }

    document.getElementById("panels").innerHTML = (story.panels || [])
      .map((p) => {
        const rateBlock = readOnly
          ? ""
          : `<label class="pe-label">Panel rating *</label>
          ${rateSelect(`p-rate-${p.index}`)}
          <label class="pe-label">Panel feedback</label>
          <textarea id="p-fb-${p.index}" rows="2" placeholder="What was good / confusing / broken?"></textarea>`;
        return `<article class="panel-card">
          <div class="panel-idx">Panel ${esc(p.index)}</div>
          <h3>${esc(p.scene_description)}</h3>
          <img class="panel-img" src="${esc(p.image)}" alt="Panel ${esc(p.index)}" loading="lazy" />
          ${p.dialogue ? `<p class="dialogue">${esc(p.dialogue)}</p>` : ""}
          ${rateBlock}
        </article>`;
      })
      .join("");

    if (readOnly) return;

    document.getElementById("submitAll").onclick = async () => {
      const overall = Number(document.getElementById("overallRating").value);
      if (!overall) {
        document.getElementById("submitStatus").textContent = "Pick overall rating.";
        return;
      }
      const panels = [];
      for (const p of story.panels || []) {
        const rating = Number(document.getElementById(`p-rate-${p.index}`).value);
        if (!rating) {
          document.getElementById("submitStatus").textContent = `Rate panel ${p.index}.`;
          return;
        }
        panels.push({
          index: p.index,
          rating,
          feedback: document.getElementById(`p-fb-${p.index}`).value.trim(),
        });
      }
      document.getElementById("submitStatus").textContent = "Submitting…";
      const post = await fetch("/api/feedback", {
        method: "POST",
        headers: Auth.headers(),
        credentials: "include",
        body: JSON.stringify({
          story_id: story.id,
          overall_rating: overall,
          overall_feedback: document.getElementById("overallFeedback").value.trim(),
          panels,
        }),
      });
      const out = await post.json().catch(() => ({}));
      if (!post.ok) {
        document.getElementById("submitStatus").textContent = out.detail || post.statusText;
        return;
      }
      document.getElementById("submitStatus").textContent = "Thanks — saved to your account.";
      document.getElementById("submitAll").disabled = true;
    };
  },
};

window.Auth = Auth;
window.AuthPage = AuthPage;
window.Home = Home;
window.StoryPage = StoryPage;
