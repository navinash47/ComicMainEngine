const { redis, json, readBody } = require("../lib/http");
const { requireUser } = require("../lib/auth");

module.exports = async (req, res) => {
  if (req.method === "OPTIONS") return json(res, 204, {});
  if (req.method !== "POST") return json(res, 405, { detail: "POST only" });
  try {
    const user = await requireUser(req);
    const body = await readBody(req);
    const storyId = String(body.story_id || "").trim();
    const answers = body.answers && typeof body.answers === "object" ? body.answers : null;
    if (!answers || !Object.keys(answers).length) {
      return json(res, 400, { detail: "answers required" });
    }

    // Light validation — required keys checked by client; truncate free text
    const cleaned = {};
    for (const [k, v] of Object.entries(answers)) {
      const key = String(k).slice(0, 80);
      cleaned[key] = String(v ?? "").slice(0, 4000);
    }

    const crypto = require("crypto");
    const id = crypto.randomUUID();
    const row = {
      id,
      type: "mom_test",
      method: "mom_test",
      reviewer_key: user.id,
      reviewer_name: user.name,
      reviewer_username: user.username,
      story_id: storyId || null,
      answers: cleaned,
      created_at: new Date().toISOString(),
      source: "vercel-reader",
    };
    const r = redis();
    await r.set(`questionnaire:${id}`, row);
    await r.lpush("questionnaire_ids", id);
    await r.ltrim("questionnaire_ids", 0, 4999);
    return json(res, 200, { ok: true, response: row });
  } catch (e) {
    return json(res, e.status || 500, { detail: String(e.message || e) });
  }
};
