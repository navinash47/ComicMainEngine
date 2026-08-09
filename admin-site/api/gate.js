const { json, checkGate } = require("../lib/http");

module.exports = async (req, res) => {
  if (req.method === "OPTIONS") return json(res, 204, {});
  if (req.method !== "GET") return json(res, 405, { detail: "GET only" });
  if (!checkGate(req, res)) return;
  return json(res, 200, {
    ok: true,
    password_required: Boolean(process.env.ADMIN_SITE_PASSWORD),
  });
};
