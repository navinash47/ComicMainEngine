const { json } = require("../lib/http");

/** Public gate probe + optional password verify (must NOT 401 when probing). */
module.exports = async (req, res) => {
  if (req.method === "OPTIONS") return json(res, 204, {});
  if (req.method !== "GET" && req.method !== "POST") {
    return json(res, 405, { detail: "GET or POST" });
  }
  const expected = process.env.ADMIN_SITE_PASSWORD || "";
  if (!expected) {
    return json(res, 200, { ok: true, password_required: false });
  }

  let got = req.headers["x-admin-password"] || "";
  if (!got && req.method === "POST") {
    try {
      const chunks = [];
      for await (const c of req) chunks.push(c);
      const body = JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}");
      got = String(body.password || "");
    } catch {
      got = "";
    }
  }

  if (!got) {
    // Unauthenticated probe — tell the client to show the gate UI
    return json(res, 200, { ok: false, password_required: true });
  }
  if (got !== expected) {
    return json(res, 401, { ok: false, password_required: true, detail: "Wrong password" });
  }
  return json(res, 200, { ok: true, password_required: true });
};
