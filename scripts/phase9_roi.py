#!/usr/bin/env python3
"""Phase 9 — mark ROI dashboard ready and print unit economics snapshot."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.roi import roi_dashboard
from comicengine.tasks import observer


def main() -> None:
    observer.upsert(
        "phase9",
        title="Phase 9 — ROI dashboard",
        description="/roi cost unit-economics + charts",
        phase="phase9",
        sort_order=90,
        status="in_progress",
        progress=0.5,
    )
    data = roi_dashboard()
    out = ROOT / "outputs" / "phase9" / "roi_snapshot.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    slim = {
        "totals": data["totals"],
        "unit_economics": data["unit_economics"],
        "insights": data["insights"],
        "by_phase": data["by_phase"],
        "by_category": data["by_category"],
    }
    out.write_text(json.dumps(slim, indent=2))
    observer.complete("phase9", note=f"ROI ready → /roi · snapshot {out}")
    print(json.dumps(slim["unit_economics"], indent=2))
    print("insights:")
    for line in slim["insights"]:
        print("-", line)
    print(f"wrote {out}")
    print("open http://127.0.0.1:8765/roi")


if __name__ == "__main__":
    main()
