const { json, checkGate, redisOrNull } = require("../lib/http");

/** Live reader feedback from shared Upstash (same DB as reader site), fallback empty. */
module.exports = async (req, res) => {
  if (req.method === "OPTIONS") return json(res, 204, {});
  if (req.method !== "GET") return json(res, 405, { detail: "GET only" });
  if (!checkGate(req, res)) return;
  try {
    const r = redisOrNull();
    if (!r) {
      return json(res, 200, {
        source: "none",
        hint: "Connect same Upstash as reader, or use /data/story_feedback.json snapshot",
        items: [],
      });
    }
    const ids = (await r.lrange("story_feedback_ids", 0, 199)) || [];
    const items = [];
    for (const id of ids) {
      const row = await r.get(`story_feedback:${id}`);
      if (row) items.push(row);
    }
    const users = (await r.smembers("users")) || [];
    return json(res, 200, {
      source: "upstash",
      summary: { responses: items.length, registered_users: users.length },
      items,
    });
  } catch (e) {
    return json(res, 500, { detail: String(e.message || e) });
  }
};
