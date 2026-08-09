#!/usr/bin/env python3
"""Phase 0.5 — generate a short bedtime AI script for the CJP test episode."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.config import OUTPUTS
from comicengine.script_engine import generate_cjp_test_episode
from comicengine.tasks import observer


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--panels", type=int, default=12, help="Keep small to save tokens")
    p.add_argument("--model", default=None, help="Defaults to auto/cheap via OmniRoute")
    args = p.parse_args()

    out_dir = OUTPUTS / "phase0.5"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "episode_cjp_origin.json"

    observer.upsert(
        "phase0.5",
        title="Phase 0.5 — AI script engine (CJP test)",
        description="Bedtime episode JSON with CJP cast",
        phase="phase0.5",
        sort_order=7,
        status="in_progress",
        progress=0.1,
    )
    try:
        episode = generate_cjp_test_episode(panel_count=args.panels, model=args.model)
        out_path.write_text(episode.model_dump_json(indent=2))
        observer.complete("phase0.5", note=f"wrote {out_path.name} ({len(episode.panels)} panels)")
        print(f"saved {out_path}")
        print(f"title: {episode.title}")
        print(f"panels: {len(episode.panels)}")
        print(f"summary: {episode.narrative_summary[:240]}...")
    except Exception as e:  # noqa: BLE001
        observer.fail("phase0.5", str(e))
        raise


if __name__ == "__main__":
    main()
