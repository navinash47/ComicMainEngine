const { redis, json, readBody } = require("../lib/http");
const { requireUser } = require("../lib/auth");

module.exports = async (req, res) => {
  if (req.method === "OPTIONS") return json(res, 204, {});
  if (req.method !== "POST") return json(res, 405, { detail: "POST only" });
  try {
    const user = await requireUser(req);
    const body = await readBody(req);
    const storyId = String(body.story_id || "").trim();
    const overall = Number(body.overall_rating);
    if (!storyId) return json(res, 400, { detail: "story_id required" });
    if (!(overall >= 1 && overall <= 5)) return json(res, 400, { detail: "overall_rating 1–5" });

    const panels = Array.isArray(body.panels) ? body.panels : [];
    const cleaned = [];
    for (const p of panels) {
      const idx = Number(p.index);
      const rating = Number(p.rating);
      if (!(idx >= 1) || !(rating >= 1 && rating <= 5)) {
        return json(res, 400, { detail: `invalid panel rating for index ${p.index}` });
      }
      cleaned.push({
        index: idx,
        rating,
        feedback: String(p.feedback || "").slice(0, 2000),
      });
    }
    if (!cleaned.length) return json(res, 400, { detail: "panels required" });

    const crypto = require("crypto");
    const id = crypto.randomUUID();
    const row = {
      id,
      reviewer_key: user.id,
      reviewer_name: user.name,
      reviewer_username: user.username,
      story_id: storyId,
      overall_rating: overall,
      overall_feedback: String(body.overall_feedback || "").slice(0, 4000),
      panels: cleaned,
      created_at: new Date().toISOString(),
      source: "vercel-reader",
    };
    const r = redis();
    await r.set(`story_feedback:${id}`, row);
    await r.lpush("story_feedback_ids", id);
    await r.ltrim("story_feedback_ids", 0, 4999);
    return json(res, 200, { ok: true, response: row });
  } catch (e) {
    return json(res, e.status || 500, { detail: String(e.message || e) });
  }
};
