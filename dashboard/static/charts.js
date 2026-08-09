/** Tiny canvas charts — no CDN dependency (works offline on Vercel). */
const Charts = {
  /** Stable CSS box size — never read canvas.height after we touch the bitmap. */
  size(canvas) {
    const cssH = Number(canvas.getAttribute("height")) || Number(canvas.dataset.cssHeight) || 160;
    canvas.dataset.cssHeight = String(cssH);
    canvas.style.width = "100%";
    canvas.style.height = `${cssH}px`;
    const cssW = Math.max(200, Math.floor(canvas.clientWidth || canvas.parentElement?.clientWidth || 320));
    return { cssW, cssH };
  },
  clear(canvas) {
    const ctx = canvas.getContext("2d");
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const { cssW, cssH } = this.size(canvas);
    // Only reset bitmap when size actually changed — avoids layout thrash
    const bw = Math.floor(cssW * dpr);
    const bh = Math.floor(cssH * dpr);
    if (canvas.width !== bw || canvas.height !== bh) {
      canvas.width = bw;
      canvas.height = bh;
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssW, cssH);
    return { ctx, w: cssW, h: cssH };
  },
  colors: {
    ink: "#f3e6d4",
    muted: "#b9a893",
    accent: "#d9773a",
    bar: "#e8b07a",
    line: "rgba(243,230,212,0.12)",
    ok: "#6fbf73",
  },
  bar(canvas, labels, values, { max } = {}) {
    const { ctx, w, h } = this.clear(canvas);
    const pad = { t: 18, r: 12, b: 36, l: 28 };
    const iw = w - pad.l - pad.r;
    const ih = h - pad.t - pad.b;
    const vals = (values || []).map((v) => Number(v) || 0);
    const m = max || Math.max(...vals, 1);
    const n = Math.max(vals.length, 1);
    const gap = 8;
    const bw = Math.max(8, (iw - gap * (n - 1)) / n);
    ctx.strokeStyle = this.colors.line;
    ctx.beginPath();
    ctx.moveTo(pad.l, pad.t);
    ctx.lineTo(pad.l, pad.t + ih);
    ctx.lineTo(pad.l + iw, pad.t + ih);
    ctx.stroke();
    vals.forEach((v, i) => {
      const x = pad.l + i * (bw + gap);
      const bh = (v / m) * ih;
      const y = pad.t + ih - bh;
      const g = ctx.createLinearGradient(0, y, 0, y + Math.max(bh, 1));
      g.addColorStop(0, "#e8b07a");
      g.addColorStop(1, "#c46a2e");
      ctx.fillStyle = g;
      ctx.fillRect(x, y, bw, Math.max(v > 0 ? 2 : 0, bh));
      ctx.fillStyle = this.colors.muted;
      ctx.font = "11px Avenir Next, Segoe UI, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(String(labels[i] ?? ""), x + bw / 2, h - 14);
      if (v) {
        ctx.fillStyle = this.colors.ink;
        ctx.fillText(String(v), x + bw / 2, Math.max(pad.t + 10, y - 4));
      }
    });
  },
  line(canvas, labels, values) {
    const { ctx, w, h } = this.clear(canvas);
    const pad = { t: 18, r: 12, b: 36, l: 28 };
    const iw = w - pad.l - pad.r;
    const ih = h - pad.t - pad.b;
    const vals = (values || []).map((v) => Number(v) || 0);
    const m = Math.max(...vals, 1);
    ctx.strokeStyle = this.colors.line;
    ctx.strokeRect(pad.l, pad.t, iw, ih);
    if (!vals.length) {
      ctx.fillStyle = this.colors.muted;
      ctx.font = "12px Avenir Next, Segoe UI, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("No login events yet", w / 2, h / 2);
      return;
    }
    ctx.strokeStyle = this.colors.accent;
    ctx.lineWidth = 2;
    ctx.beginPath();
    vals.forEach((v, i) => {
      const x = pad.l + (vals.length === 1 ? iw / 2 : (i / (vals.length - 1)) * iw);
      const y = pad.t + ih - (v / m) * ih;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    vals.forEach((v, i) => {
      const x = pad.l + (vals.length === 1 ? iw / 2 : (i / (vals.length - 1)) * iw);
      const y = pad.t + ih - (v / m) * ih;
      ctx.fillStyle = this.colors.bar;
      ctx.beginPath();
      ctx.arc(x, y, 3.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = this.colors.muted;
      ctx.font = "10px Avenir Next, Segoe UI, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(String(labels[i] || "").slice(5), x, h - 14);
    });
  },
};

window.Charts = Charts;
