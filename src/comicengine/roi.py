"""Phase 9 — ROI / cost analytics derived from SQLite usage ledger."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from comicengine.analytics import analytics
from comicengine.curation import curation
from comicengine.library import load_catalog
from comicengine.usage import UsageDB


def _category_of(meta_json: str | None, purpose: str | None) -> str:
    try:
        meta = json.loads(meta_json or "{}")
    except json.JSONDecodeError:
        meta = {}
    cat = (meta.get("category") or "").lower()
    if cat in {"text", "image", "usage"}:
        return cat
    p = (purpose or "").lower()
    if any(k in p for k in ("image", "panel", "char_", "flux", "gemini")):
        return "image"
    if any(k in p for k in ("script", "judge", "hello", "chat", "text")):
        return "text"
    return "other"


def roi_dashboard(db: UsageDB | None = None) -> dict[str, Any]:
    db = db or UsageDB()
    base = db.summary()
    dash = analytics.dashboard(limit=300)

    by_category: dict[str, dict[str, Any]] = {}
    by_purpose: dict[str, dict[str, Any]] = {}
    daily: dict[str, float] = {}

    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT phase, provider, model, purpose, cost_usd, ok, latency_ms, meta_json, substr(ts,1,10) AS day
            FROM api_call
            ORDER BY id ASC
            """
        ).fetchall()

    for r in rows:
        cat = _category_of(r["meta_json"], r["purpose"])
        bucket = by_category.setdefault(
            cat, {"category": cat, "calls": 0, "ok": 0, "errors": 0, "cost_usd": 0.0, "latency_ms_sum": 0}
        )
        bucket["calls"] += 1
        bucket["cost_usd"] += float(r["cost_usd"] or 0)
        bucket["latency_ms_sum"] += int(r["latency_ms"] or 0)
        if r["ok"]:
            bucket["ok"] += 1
        else:
            bucket["errors"] += 1

        purpose = r["purpose"] or "(none)"
        pb = by_purpose.setdefault(
            purpose, {"purpose": purpose, "calls": 0, "cost_usd": 0.0}
        )
        pb["calls"] += 1
        pb["cost_usd"] += float(r["cost_usd"] or 0)

        day = r["day"] or "unknown"
        daily[day] = daily.get(day, 0.0) + float(r["cost_usd"] or 0)

    category_rows = []
    for b in by_category.values():
        calls = max(b["calls"], 1)
        category_rows.append(
            {
                **b,
                "avg_latency_ms": round(b["latency_ms_sum"] / calls, 1),
                "success_rate": round(b["ok"] / calls, 3),
            }
        )
    category_rows.sort(key=lambda x: x["cost_usd"], reverse=True)

    purpose_rows = sorted(by_purpose.values(), key=lambda x: x["cost_usd"], reverse=True)[:20]
    daily_rows = [{"day": d, "cost_usd": round(c, 6)} for d, c in sorted(daily.items())]

    # Unit economics from known production artifacts
    catalog = load_catalog(refresh=False)
    stories = catalog.get("stories") or []
    story_count = max(len(stories), 1)
    panel_count = sum(int(s.get("panel_count") or 0) for s in stories) or 44
    totals = base.get("totals") or {}
    total_cost = float(totals.get("cost_usd") or 0)

    phase_map = {p["phase"]: float(p["cost_usd"] or 0) for p in base.get("by_phase") or []}
    unit = {
        "stories": len(stories),
        "panels": panel_count,
        "cost_per_story_usd": round(total_cost / story_count, 4),
        "cost_per_panel_all_in_usd": round(total_cost / max(panel_count, 1), 4),
        "phase5_panel_batch_usd": round(phase_map.get("phase5", 0.0), 4),
        "phase5_cost_per_panel_usd": round(phase_map.get("phase5", 0.0) / max(panel_count, 1), 4),
        "script_phase4_usd": round(phase_map.get("phase4", 0.0), 4),
        "compose_assemble_usd": 0.0,  # local Pillow — tracked as ~0 API
        "projected_100_episodes_usd": round((total_cost / story_count) * 100, 2),
    }

    # ROI narrative metrics
    curation_summary = curation.summary()
    approved_panels = sum(
        int(s.get("approved") or 0)
        for s in curation_summary.get("by_story") or []
    )
    # approved counts include episode rows; prefer panel-only approved from items
    approved_panel_items = len(
        [i for i in curation.list(kind="panel") if i.get("status") == "approved"]
    )

    recommendations = dash.get("recommendations") or []
    providers = base.get("by_provider") or []
    top_provider = providers[0]["provider"] if providers else None
    image_share = 0.0
    text_share = 0.0
    for c in category_rows:
        if c["category"] == "image" and total_cost:
            image_share = c["cost_usd"] / total_cost
        if c["category"] == "text" and total_cost:
            text_share = c["cost_usd"] / total_cost

    insights = [
        f"Total R&D spend ${total_cost:.3f} across {totals.get('calls', 0)} API calls.",
        f"Image share ≈ {image_share:.0%} of spend; text ≈ {text_share:.0%}.",
        f"Blended all-in ≈ ${unit['cost_per_story_usd']:.3f}/story and ${unit['cost_per_panel_all_in_usd']:.4f}/panel.",
        f"Phase 5 panel batch alone ≈ ${unit['phase5_cost_per_panel_usd']:.4f}/panel.",
        f"Projected 100 episodes at current blend ≈ ${unit['projected_100_episodes_usd']:.2f} (scripts+images+retries).",
    ]
    if top_provider:
        insights.append(f"Highest-spend provider: {top_provider}.")
    if approved_panel_items:
        insights.append(f"Curation: {approved_panel_items} panels approved so far.")

    return {
        "totals": totals,
        "by_phase": base.get("by_phase") or [],
        "by_provider": providers,
        "by_model": (base.get("by_model") or [])[:15],
        "by_category": category_rows,
        "by_purpose": purpose_rows,
        "daily": daily_rows,
        "series": base.get("series") or [],
        "unit_economics": unit,
        "insights": insights,
        "recommendations": recommendations[:8],
        "curation": curation_summary,
        "library": {"count": catalog.get("count"), "stories": [
            {"id": s.get("id"), "title": s.get("title"), "panels": s.get("panel_count")}
            for s in stories
        ]},
        "server_time": base.get("server_time"),
        "db_path": base.get("db_path"),
    }
