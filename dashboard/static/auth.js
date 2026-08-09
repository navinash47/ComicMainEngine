/** Shared auth chrome for beta pages. */
async function loadAuthChrome(opts = {}) {
  const requireAdmin = Boolean(opts.requireAdmin);
  const mountId = opts.mountId || "authChrome";
  let me = { authenticated: false };
  try {
    const res = await fetch("/api/me");
    me = await res.json();
  } catch {
    me = { authenticated: false };
  }

  let el = document.getElementById(mountId);
  if (!el) {
    el = document.createElement("div");
    el.id = mountId;
    el.className = "auth-chrome";
    const nav = document.querySelector("header .status.nav-links") || document.querySelector("header");
    if (nav) nav.appendChild(el);
    else document.body.prepend(el);
  }

  if (!me.authenticated) {
    el.innerHTML = `<a class="btn" href="/login?next=${encodeURIComponent(location.pathname)}">Sign in</a>`;
    if (requireAdmin) location.href = "/login?next=" + encodeURIComponent(location.pathname);
    return me;
  }

  const u = me.user || {};
  const adminLink = u.is_admin
    ? `<a class="btn" href="/reviewers">Reviewers</a>`
    : "";
  el.innerHTML = `
    <span class="muted small auth-who" title="${u.email || ""}">${escAuth(u.name || u.email)}</span>
    <a class="btn" href="/feedback">Feedback</a>
    ${adminLink}
    <a class="btn" href="/auth/logout">Sign out</a>
  `;

  if (requireAdmin && !u.is_admin) {
    location.href = "/library";
  }
  return me;
}

function escAuth(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

window.loadAuthChrome = loadAuthChrome;
