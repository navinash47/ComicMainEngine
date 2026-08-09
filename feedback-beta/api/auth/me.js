const { json } = require("../../lib/http");
const { userFromAuthHeader } = require("../../lib/auth");

module.exports = async (req, res) => {
  if (req.method === "OPTIONS") return json(res, 204, {});
  if (req.method !== "GET") return json(res, 405, { detail: "GET only" });
  try {
    const user = await userFromAuthHeader(req);
    return json(res, 200, { authenticated: Boolean(user), user });
  } catch (e) {
    return json(res, 500, { detail: String(e.message || e) });
  }
};
