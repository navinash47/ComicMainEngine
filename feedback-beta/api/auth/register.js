const { json, readBody, sessionCookieValue } = require("../../lib/http");
const { createUser, loginUser } = require("../../lib/auth");

module.exports = async (req, res) => {
  if (req.method === "OPTIONS") return json(res, 204, {});
  if (req.method !== "POST") return json(res, 405, { detail: "POST only" });
  try {
    const body = await readBody(req);
    const name = String(body.name || "").trim();
    const username = String(body.username || "").trim();
    const password = String(body.password || "");
    if (name && (name.length < 2 || name.length > 80)) {
      return json(res, 400, { detail: "display name 2–80 chars when set" });
    }
    if (!username) return json(res, 400, { detail: "username required" });
    if (password.length < 6) return json(res, 400, { detail: "password min 6 chars" });
    await createUser({ name, username, password });
    const session = await loginUser({ username, password });
    return json(res, 200, { ok: true, ...session }, { cookies: sessionCookieValue(session.token) });
  } catch (e) {
    return json(res, e.status || 500, { detail: String(e.message || e) });
  }
};
