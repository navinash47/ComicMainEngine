const { json, sessionCookieValue } = require("../../lib/http");
const { createGuestSession } = require("../../lib/auth");

module.exports = async (req, res) => {
  if (req.method === "OPTIONS") return json(res, 204, {});
  if (req.method !== "POST") return json(res, 405, { detail: "POST only" });
  try {
    const session = await createGuestSession();
    return json(
      res,
      200,
      { ok: true, ...session },
      { cookies: sessionCookieValue(session.token) }
    );
  } catch (e) {
    return json(res, e.status || 500, { detail: String(e.message || e) });
  }
};
