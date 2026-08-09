const { json, checkGate, redisOrNull } = require("../lib/http");

/** Live reader CRM: users, login events, feedback rolled up for admin analysis. */
module.exports = async (req, res) => {
  if (req.method === "OPTIONS") return json(res, 204, {});
  if (req.method !== "GET") return json(res, 405, { detail: "GET only" });
  if (!checkGate(req, res)) return;
  try {
    const r = redisOrNull();
    if (!r) {
      return json(res, 200, {
        source: "none",
        hint: "Connect same Upstash Redis as the reader site",
        users: [],
        login_events: [],
        feedback: [],
        charts: emptyCharts(),
      });
    }

    const userIds = (await r.smembers("users")) || [];
    const users = [];
    for (const id of userIds) {
      const u = await r.get(`user:${id}`);
      if (!u) continue;
      users.push({
        id: u.id,
        username: u.username,
        name: u.name,
        created_at: u.created_at,
        last_login_at: u.last_login_at || null,
        login_count: Number(u.login_count || 0),
      });
    }

    const login_events = (await r.lrange("login_events", 0, 99)) || [];
    const fbIds = (await r.lrange("story_feedback_ids", 0, 499)) || [];
    const feedback = [];
    for (const id of fbIds) {
      const row = await r.get(`story_feedback:${id}`);
      if (row) feedback.push(row);
    }

    const byUser = {};
    for (const u of users) {
      byUser[u.id] = {
        ...u,
        responses: [],
        avg_overall: null,
        stories_rated: 0,
        panel_ratings: 0,
      };
    }
    for (const item of feedback) {
      const key = item.reviewer_key;
      if (!byUser[key]) {
        byUser[key] = {
          id: key,
          username: item.reviewer_username || null,
          name: item.reviewer_name || "unknown",
          created_at: null,
          last_login_at: null,
          login_count: 0,
          responses: [],
          avg_overall: null,
          stories_rated: 0,
          panel_ratings: 0,
        };
      }
      byUser[key].responses.push(item);
    }
    const people = Object.values(byUser).map((p) => {
      const overalls = p.responses.map((x) => Number(x.overall_rating)).filter((n) => n >= 1);
      const panels = p.responses.flatMap((x) => x.panels || []);
      return {
        ...p,
        stories_rated: p.responses.length,
        panel_ratings: panels.length,
        avg_overall: overalls.length
          ? Math.round((overalls.reduce((a, b) => a + b, 0) / overalls.length) * 100) / 100
          : null,
        avg_panel: panels.length
          ? Math.round(
              (panels.reduce((a, b) => a + Number(b.rating || 0), 0) / panels.length) * 100
            ) / 100
          : null,
      };
    });
    people.sort((a, b) => String(b.last_login_at || b.created_at || "").localeCompare(String(a.last_login_at || a.created_at || "")));

    const charts = buildCharts(feedback, login_events, people);

    return json(res, 200, {
      source: "upstash",
      fetched_at: new Date().toISOString(),
      summary: {
        registered_users: users.length,
        login_events: login_events.length,
        feedback_responses: feedback.length,
        people_with_feedback: people.filter((p) => p.stories_rated > 0).length,
      },
      people,
      login_events,
      feedback,
      charts,
    });
  } catch (e) {
    return json(res, 500, { detail: String(e.message || e) });
  }
};

function emptyCharts() {
  return {
    ratings_hist: [0, 0, 0, 0, 0],
    by_story: [],
    logins_by_day: [],
    panel_avg_by_story: [],
  };
}

function buildCharts(feedback, login_events, people) {
  const ratings_hist = [0, 0, 0, 0, 0];
  const storyMap = {};
  for (const item of feedback) {
    const o = Number(item.overall_rating);
    if (o >= 1 && o <= 5) ratings_hist[o - 1] += 1;
    const sid = item.story_id || "unknown";
    if (!storyMap[sid]) storyMap[sid] = { story_id: sid, responses: 0, overall_sum: 0, panels: [] };
    storyMap[sid].responses += 1;
    storyMap[sid].overall_sum += o || 0;
    for (const p of item.panels || []) storyMap[sid].panels.push(Number(p.rating) || 0);
  }
  const by_story = Object.values(storyMap).map((s) => ({
    story_id: s.story_id,
    responses: s.responses,
    avg_overall: s.responses ? Math.round((s.overall_sum / s.responses) * 100) / 100 : 0,
    avg_panel: s.panels.length
      ? Math.round((s.panels.reduce((a, b) => a + b, 0) / s.panels.length) * 100) / 100
      : 0,
  }));

  const dayMap = {};
  for (const ev of login_events) {
    const at = (ev && ev.at) || "";
    const day = String(at).slice(0, 10) || "unknown";
    dayMap[day] = (dayMap[day] || 0) + 1;
  }
  const logins_by_day = Object.entries(dayMap)
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([day, count]) => ({ day, count }));

  return {
    ratings_hist,
    by_story,
    logins_by_day,
    top_reviewers: people
      .filter((p) => p.stories_rated)
      .sort((a, b) => b.stories_rated - a.stories_rated)
      .slice(0, 8)
      .map((p) => ({
        name: p.name || p.username,
        stories_rated: p.stories_rated,
        avg_overall: p.avg_overall,
      })),
  };
}
