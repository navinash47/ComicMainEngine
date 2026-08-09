const $ = (id) => document.getElementById(id);
let data = { generated: [], cjp_refs: [], attribution: "" };
let tab = "generated";

function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function render() {
  const rows = tab === "cjp" ? data.cjp_refs || [] : data.generated || [];
  $("attr").textContent = tab === "cjp" ? data.attribution || "" : "Local pipeline outputs under outputs/.";
  if (!rows.length) {
    $("grid").innerHTML =
      tab === "cjp"
        ? `<p class="muted">No CJP refs yet — run <code>python scripts/fetch_cjp_refs.py</code>.</p>`
        : `<p class="muted">No generated images yet — run Phase 1.</p>`;
    return;
  }
  $("grid").innerHTML = rows
    .map((img) => {
      const meta =
        tab === "cjp"
          ? `${esc(img.license || "")} · ${esc(img.artist || "unknown")} · ${esc(img.role || "")}`
          : `${esc(img.phase || "")} · ${fmtBytes(img.bytes)}`;
      const link = img.commons_url
        ? `<a href="${esc(img.commons_url)}" target="_blank" rel="noreferrer">Commons</a>`
        : "";
      return `<figure class="image-card">
        <a href="${esc(img.href)}" target="_blank" rel="noreferrer">
          <img src="${esc(img.href)}" alt="${esc(img.title)}" loading="lazy" />
        </a>
        <figcaption>
          <div class="title">${esc(img.title)}</div>
          <div class="desc">${meta}</div>
          ${img.note ? `<div class="desc">${esc(img.note)}</div>` : ""}
          ${link}
        </figcaption>
      </figure>`;
    })
    .join("");
}

function fmtBytes(n) {
  n = Number(n) || 0;
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("on"));
    btn.classList.add("on");
    tab = btn.dataset.tab;
    render();
  });
});

async function load() {
  const res = await fetch("/api/images");
  data = await res.json();
  $("updated").textContent = `updated ${new Date().toLocaleTimeString()}`;
  render();
}

load();
setInterval(load, 5000);
