const { Redis } = require("@upstash/redis");

function json(res, status, body) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type,x-admin-password");
  res.end(JSON.stringify(body));
}

function checkGate(req, res) {
  const expected = process.env.ADMIN_SITE_PASSWORD || "";
  if (!expected) return true; // open when unset (repo-private URL)
  const got = req.headers["x-admin-password"] || "";
  if (got !== expected) {
    json(res, 401, { detail: "admin password required" });
    return false;
  }
  return true;
}

function redisOrNull() {
  const url = process.env.UPSTASH_REDIS_REST_URL || process.env.KV_REST_API_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN || process.env.KV_REST_API_TOKEN;
  if (!url || !token) return null;
  return new Redis({ url, token });
}

module.exports = { json, checkGate, redisOrNull };
