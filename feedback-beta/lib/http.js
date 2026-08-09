const { Redis } = require("@upstash/redis");

const SESSION_COOKIE = "ce_session";
const SESSION_MAX_AGE = 60 * 60 * 24 * 30; // 30d

function redis() {
  const url = process.env.UPSTASH_REDIS_REST_URL || process.env.KV_REST_API_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN || process.env.KV_REST_API_TOKEN;
  if (!url || !token) {
    throw new Error("Set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN (Vercel Upstash integration)");
  }
  return new Redis({ url, token });
}

function parseCookies(req) {
  const raw = req.headers.cookie || "";
  const out = {};
  for (const part of raw.split(";")) {
    const i = part.indexOf("=");
    if (i < 0) continue;
    const k = part.slice(0, i).trim();
    const v = part.slice(i + 1).trim();
    if (k) out[k] = decodeURIComponent(v);
  }
  return out;
}

function sessionCookieValue(token, { clear = false } = {}) {
  if (clear || !token) {
    return `${SESSION_COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`;
  }
  return `${SESSION_COOKIE}=${encodeURIComponent(token)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${SESSION_MAX_AGE}`;
}

function json(res, status, body, { cookies } = {}) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  res.setHeader(
    "Access-Control-Allow-Headers",
    "Content-Type,Authorization,x-admin-secret,x-session-token"
  );
  if (cookies) {
    const list = Array.isArray(cookies) ? cookies : [cookies];
    res.setHeader("Set-Cookie", list);
  }
  res.end(JSON.stringify(body));
}

async function readBody(req) {
  const bufs = [];
  for await (const c of req) bufs.push(c);
  if (!bufs.length) return {};
  try {
    return JSON.parse(Buffer.concat(bufs).toString("utf8") || "{}");
  } catch {
    return {};
  }
}

module.exports = {
  redis,
  json,
  readBody,
  parseCookies,
  sessionCookieValue,
  SESSION_COOKIE,
};
