const { json, sessionCookieValue } = require("../../lib/http");
const { destroySession } = require("../../lib/auth");

module.exports = async (req, res) => {
  if (req.method === "OPTIONS") return json(res, 204, {});
  if (req.method !== "POST") return json(res, 405, { detail: "POST only" });
  try {
    await destroySession(req);
    return json(res, 200, { ok: true }, { cookies: sessionCookieValue("", { clear: true }) });
  } catch (e) {
    return json(res, 500, { detail: String(e.message || e) });
  }
};
