#!/usr/bin/env python3
"""Phase 4 — generate Et tu Brutus + Hitler warning scripts (alongside CJP)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.config import OUTPUTS
from comicengine.script_engine import STORIES, generate_episode
from comicengine.stories import list_stories
from comicengine.tasks import observer

DEFAULT_KEYS = ["et_tu_brutus", "hitler_warning"]


def main() -> None:
    p = argparse.ArgumentParser(description="Phase 4 multi-story script generation")
    p.add_argument(
        "--stories",
        default=",".join(DEFAULT_KEYS),
        help=f"Comma keys from {sorted(STORIES)} (default: {','.join(DEFAULT_KEYS)})",
    )
    p.add_argument("--panels", type=int, default=16)
    p.add_argument("--model", default=None)
    args = p.parse_args()

    keys = [k.strip() for k in args.stories.split(",") if k.strip()]
    for k in keys:
        if k not in STORIES:
            raise SystemExit(f"unknown story {k!r}; choose {sorted(STORIES)}")

    out_dir = OUTPUTS / "phase4"
    out_dir.mkdir(parents=True, exist_ok=True)

    observer.upsert(
        "phase4",
        title="Phase 4 — Multi-topic LLM scripts",
        description="Et tu Brutus + Hitler warning (teen didactic) beside CJP",
        phase="phase4",
        sort_order=40,
        status="in_progress",
        progress=0.05,
        meta={"stories": keys},
    )

    written: list[Path] = []
    try:
        for i, key in enumerate(keys):
            spec = STORIES[key]
            observer.set_progress(
                "phase4",
                0.1 + 0.8 * (i / max(len(keys), 1)),
                note=f"generating {key}…",
            )
            episode = generate_episode(
                key,
                panel_count=args.panels,
                model=args.model,
                phase="phase4",
            )
            out_path = out_dir / f"{spec.file_stem}.json"
            out_path.write_text(episode.model_dump_json(indent=2))
            written.append(out_path)
            print(f"saved {out_path}")
            print(f"  title: {episode.title}")
            print(f"  panels: {len(episode.panels)}  voice: {episode.voice}")
            print(f"  summary: {episode.narrative_summary[:220]}…")

        stories = list_stories()
        ids = [s["id"] for s in stories]
        observer.complete(
            "phase4",
            note=f"wrote {[p.name for p in written]}; dashboard stories={ids}",
        )
        print("dashboard story ids:", ids)
    except Exception as e:  # noqa: BLE001
        observer.fail("phase4", str(e))
        raise


if __name__ == "__main__":
    main()
