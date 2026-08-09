#!/usr/bin/env python3
"""Export engine snapshots into admin-site/public/data for Vercel deploy."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.roi import roi_dashboard
from comicengine.story_feedback import story_feedback
from comicengine.tasks import observer
from comicengine.usage import UsageDB

DEST = ROOT / "admin-site" / "public" / "data"


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    db = UsageDB()
    usage = db.summary()
    roi = roi_dashboard(db)
    tasks = observer.snapshot()
    fb = {
        "summary": story_feedback.summary(),
        "items": story_feedback.list(limit=500),
    }

    phase_notes = [
        {"id": "phase0", "title": "API pings", "status": "complete"},
        {"id": "phase0.5", "title": "AI scripts", "status": "complete"},
        {"id": "phase1–3", "title": "fal + style + consistency", "status": "complete"},
        {"id": "phase4–5", "title": "Multi-story scripts + panel batch", "status": "complete"},
        {"id": "phase6–7.5", "title": "Compose + assemble + library", "status": "complete"},
        {"id": "phase8–8.6", "title": "Curation + ratings + public review", "status": "complete"},
        {"id": "phase9–11", "title": "ROI + publish export + cost guardrails", "status": "complete"},
        {"id": "phase12+", "title": "Version 2 (post-feedback features)", "status": "planned"},
    ]

    overview = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "project": "ComicMainEngine / onceuponatime",
        "github": "https://github.com/navinash47/ComicMainEngine",
        "audience": "fellow developers + owner",
        "local_admin": "http://127.0.0.1:8765/admin",
        "local_review": "http://127.0.0.1:8765/review",
        "notes": [
            "This Vercel admin is a read-only engine console for sharing with fellowdevs.",
            "Live image regen / OmniRoute scripting still run locally (or a GPU/API host).",
            "Reader feedback appears below when prepared from SQLite, or live via shared Upstash.",
            "Version 2 starts at Phase 12 after Mom Test / panel feedback review.",
        ],
        "phases": phase_notes,
        "routing": {
            "text_llm": "OmniRoute localhost:20128 (coding/scripts only)",
            "images": "Direct GOOGLE_API_KEY / fal from .env — never OmniRoute",
        },
    }

    (DEST / "overview.json").write_text(json.dumps(overview, indent=2), encoding="utf-8")
    (DEST / "usage.json").write_text(json.dumps(usage, indent=2), encoding="utf-8")
    (DEST / "roi.json").write_text(json.dumps(roi, indent=2), encoding="utf-8")
    (DEST / "tasks.json").write_text(json.dumps(tasks, indent=2), encoding="utf-8")
    (DEST / "story_feedback.json").write_text(json.dumps(fb, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "dest": str(DEST.relative_to(ROOT)),
                "calls": (usage.get("totals") or {}).get("calls"),
                "cost_usd": (usage.get("totals") or {}).get("cost_usd"),
                "feedback_rows": fb["summary"].get("responses"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
