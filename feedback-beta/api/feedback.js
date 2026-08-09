const { redis, json, readBody } = require("../lib/http");
const { requireUser } = require("../lib/auth");

function cleanPanel(p) {
  const idx = Number(p.index);
  const ratingRaw = p.rating;
  const rating = ratingRaw === "" || ratingRaw == null ? null : Number(ratingRaw);
  const feedback = String(p.feedback || "").slice(0, 2000);
  if (!(idx >= 1)) return { error: `invalid panel index ${p.index}` };
  if (rating != null && !(rating >= 1 && rating <= 5)) {
    return { error: `invalid panel rating for index ${p.index}` };
  }
  if (rating == null && !feedback) {
    return { error: `panel ${idx} needs a rating or feedback` };
  }
  return {
    panel: {
      index: idx,
      rating,
      feedback,
    },
  };
}

module.exports = async (req, res) => {
  if (req.method === "OPTIONS") return json(res, 204, {});
  if (req.method !== "POST") return json(res, 405, { detail: "POST only" });
  try {
    const user = await requireUser(req);
    const body = await readBody(req);
    const storyId = String(body.story_id || "").trim();
    if (!storyId) return json(res, 400, { detail: "story_id required" });

    const kind = String(body.kind || "story").toLowerCase();
    const crypto = require("crypto");
    const id = crypto.randomUUID();
    const base = {
      id,
      kind,
      reviewer_key: user.id,
      reviewer_name: user.name,
      reviewer_username: user.username,
      story_id: storyId,
      created_at: new Date().toISOString(),
      source: "vercel-reader",
    };

    let row;
    if (kind === "panel") {
      const raw = body.panel || (Array.isArray(body.panels) ? body.panels[0] : null);
      if (!raw) return json(res, 400, { detail: "panel required" });
      const cleaned = cleanPanel(raw);
      if (cleaned.error) return json(res, 400, { detail: cleaned.error });
      row = {
        ...base,
        overall_rating: null,
        overall_feedback: "",
        character_consistency: null,
        character_consistency_feedback: "",
        other_feedback: "",
        panels: [cleaned.panel],
      };
    } else {
      const overall = Number(body.overall_rating);
      if (!(overall >= 1 && overall <= 5)) {
        return json(res, 400, { detail: "overall_rating 1–5" });
      }
      let charCon = body.character_consistency;
      charCon = charCon === "" || charCon == null ? null : Number(charCon);
      if (charCon != null && !(charCon >= 1 && charCon <= 5)) {
        return json(res, 400, { detail: "character_consistency 1–5" });
      }

      const panelsIn = Array.isArray(body.panels) ? body.panels : [];
      const cleaned = [];
      for (const p of panelsIn) {
        // skip empty optional panel rows
        const ratingRaw = p.rating;
        const feedback = String(p.feedback || "").trim();
        if ((ratingRaw === "" || ratingRaw == null) && !feedback) continue;
        const one = cleanPanel(p);
        if (one.error) return json(res, 400, { detail: one.error });
        cleaned.push(one.panel);
      }

      row = {
        ...base,
        overall_rating: overall,
        overall_feedback: String(body.overall_feedback || "").slice(0, 4000),
        character_consistency: charCon,
        character_consistency_feedback: String(
          body.character_consistency_feedback || ""
        ).slice(0, 4000),
        other_feedback: String(body.other_feedback || "").slice(0, 4000),
        panels: cleaned,
      };
    }

    const r = redis();
    await r.set(`story_feedback:${id}`, row);
    await r.lpush("story_feedback_ids", id);
    await r.ltrim("story_feedback_ids", 0, 4999);
    return json(res, 200, { ok: true, response: row });
  } catch (e) {
    return json(res, e.status || 500, { detail: String(e.message || e) });
  }
};
