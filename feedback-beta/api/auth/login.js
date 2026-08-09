const { json, readBody, sessionCookieValue } = require("../../lib/http");
const { loginUser } = require("../../lib/auth");

module.exports = async (req, res) => {
  if (req.method === "OPTIONS") return json(res, 204, {});
  if (req.method !== "POST") return json(res, 405, { detail: "POST only" });
  try {
    const body = await readBody(req);
    const username = String(body.username || body.email || "").trim();
    const password = String(body.password || "");
    const session = await loginUser({ username, password });
    return json(res, 200, { ok: true, ...session }, { cookies: sessionCookieValue(session.token) });
  } catch (e) {
    return json(res, e.status || 500, { detail: String(e.message || e) });
  }
};
