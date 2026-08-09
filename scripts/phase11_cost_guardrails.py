#!/usr/bin/env python3
"""Phase 11 — cost guardrails baseline before Version 2 (Phase 12+)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.roi import roi_dashboard
from comicengine.tasks import observer
from comicengine.usage import UsageDB

OUT = ROOT / "outputs" / "phase11" / "cost_guardrails.json"


def build_snapshot() -> dict:
    dash = roi_dashboard(UsageDB())
    unit = dash.get("unit_economics") or {}
    return {
        "phase": "phase11",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "guardrails": [
            "Beta review traffic: no automatic panel regen for reviewers (admin-only).",
            "Keep image gen on direct provider keys (never OmniRoute).",
            "Prefer gemini_ref; Kontext only for hard identity retries.",
            "Freeze StyleLock korean_manhwa until human taste gate closes.",
            "Version 2 (Phase 12+) may add features only after Mom Test export review.",
        ],
        "roi": {
            "cost_per_story_usd": unit.get("cost_per_story_usd"),
            "cost_per_panel_all_in_usd": unit.get("cost_per_panel_all_in_usd"),
            "projected_100_episodes_usd": unit.get("projected_100_episodes_usd"),
            "insights": dash.get("insights") or [],
        },
        "version2_starts_at": "phase12",
        "notes": (
            "Full blind cheaper-backend bake-off deferred until Mom Test feedback "
            "from beta reviewers prioritizes cost vs quality — do not burn spend early."
        ),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Phase 11 cost guardrails")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("snapshot", help="Write outputs/phase11/cost_guardrails.json")
    sub.add_parser("gate", help="Snapshot + mark phase 11 complete")
    args = p.parse_args()

    snap = build_snapshot()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snap, indent=2), encoding="utf-8")

    if args.cmd == "gate":
        observer.upsert(
            "phase11",
            title="Phase 11 — Cost optimization",
            description="Beta cost guardrails + ROI baseline (full bake-off deferred to V2)",
            phase="phase11",
            sort_order=110,
            status="in_progress",
            progress=0.5,
        )
        observer.complete(
            "phase11",
            note="guardrails snapshot written; Version 2 begins at phase12",
        )
    print(json.dumps({"ok": True, "path": str(OUT.relative_to(ROOT)), **snap}, indent=2))


if __name__ == "__main__":
    main()
