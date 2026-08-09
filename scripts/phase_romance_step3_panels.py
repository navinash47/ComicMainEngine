#!/usr/bin/env python3
"""Romance Step 3 — manhwa panel batch for HIMYM Episode 1."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

os.environ.setdefault("STYLE_ID", "korean_manhwa")

from comicengine.config import OUTPUTS
from comicengine.panel_batch import render_episode
from comicengine.tasks import observer

EPISODE = OUTPUTS / "phase4" / "episode_how_i_met_your_mother_ep1.json"


def main() -> None:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None, help="Max panels (debug)")
    p.add_argument("--no-skip", action="store_true")
    p.add_argument("--retries", type=int, default=2)
    args = p.parse_args()

    if not EPISODE.is_file():
        raise SystemExit(f"missing script — run step1 first: {EPISODE}")

    observer.upsert(
        "phase_romance_step3",
        title="Romance Step 3 — Manhwa panel batch",
        description="Episode panels with gemini_ref + feeling art prompts",
        phase="phase_romance_step3",
        sort_order=220,
        status="in_progress",
        progress=0.05,
        meta={"story": EPISODE.name},
    )
    # Unlock later steps as pending awareness
    for tid, title, desc, order in [
        (
            "phase_romance_step4",
            "Romance Step 4 — Speech bubbles",
            "Compose dialogue/captions on panels",
            230,
        ),
        (
            "phase_romance_step5",
            "Romance Step 5 — Assemble + Library",
            "Webtoon/PDF + catalog entry",
            240,
        ),
    ]:
        observer.upsert(
            tid,
            title=title,
            description=desc,
            phase=tid,
            sort_order=order,
            status="pending",
            progress=0.0,
        )

    try:
        observer.set_progress("phase_romance_step3", 0.1, note="rendering panels…")
        man = render_episode(
            EPISODE,
            phase="phase_romance_step3",
            skip_existing=not args.no_skip,
            panel_limit=args.limit,
            max_retries=args.retries,
        )
        ok, total, err = man["ok"], man["panel_count"], man["errors"]
        note = f"{ok}/{total} ok · errors={err}"
        if err == 0 and ok >= total:
            observer.complete("phase_romance_step3", note=note)
        else:
            observer.set_progress("phase_romance_step3", min(0.95, ok / max(total, 1)), note=note)
        print(f"DONE {man['story_id']}: {note}")
    except Exception as e:  # noqa: BLE001
        observer.fail("phase_romance_step3", str(e))
        raise


if __name__ == "__main__":
    main()
