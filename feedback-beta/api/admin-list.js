const { redis, json } = require("../lib/http");

module.exports = async (req, res) => {
  if (req.method === "OPTIONS") return json(res, 204, {});
  if (req.method !== "GET") return json(res, 405, { detail: "GET only" });
  const secret = req.headers["x-admin-secret"] || "";
  if (!process.env.FEEDBACK_ADMIN_SECRET || secret !== process.env.FEEDBACK_ADMIN_SECRET) {
    return json(res, 401, { detail: "admin secret required" });
  }
  try {
    const r = redis();
    const ids = (await r.lrange("story_feedback_ids", 0, 499)) || [];
    const items = [];
    for (const id of ids) {
      const row = await r.get(`story_feedback:${id}`);
      if (row) items.push(row);
    }
    const reviewerIds = (await r.smembers("reviewers")) || [];
    return json(res, 200, {
      summary: { responses: items.length, reviewers: reviewerIds.length },
      items,
    });
  } catch (e) {
    return json(res, 500, { detail: String(e.message || e) });
  }
};
