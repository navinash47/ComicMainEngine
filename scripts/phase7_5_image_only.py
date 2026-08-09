#!/usr/bin/env python3
"""Phase 7.5 — Only Image episode assembly (raw Phase 5 panels, no speech bubbles)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.assembler import assemble_episode
from comicengine.config import OUTPUTS
from comicengine.episode_schema import Episode
from comicengine.library import rebuild_catalog
from comicengine.tasks import observer

DEFAULT = [
    OUTPUTS / "phase0.5" / "episode_cjp_origin.json",
    OUTPUTS / "phase4" / "episode_et_tu_brutus.json",
    OUTPUTS / "phase4" / "episode_hitler_warning.json",
]


def main() -> None:
    p = argparse.ArgumentParser(description="Phase 7.5 Only-Image assembler")
    p.add_argument("--stories", default="all")
    p.add_argument("--width", type=int, default=900)
    p.add_argument("--no-skip", action="store_true")
    args = p.parse_args()

    if args.stories.strip() == "all":
        paths = list(DEFAULT)
    else:
        stem_map = {
            "cjp": DEFAULT[0],
            "episode_cjp_origin": DEFAULT[0],
            "et_tu_brutus": DEFAULT[1],
            "episode_et_tu_brutus": DEFAULT[1],
            "hitler_warning": DEFAULT[2],
            "episode_hitler_warning": DEFAULT[2],
        }
        paths = []
        for key in args.stories.split(","):
            key = key.strip()
            if key not in stem_map:
                raise SystemExit(f"unknown story {key}")
            paths.append(stem_map[key])

    observer.upsert(
        "phase7.5",
        title="Phase 7.5 — Only Image assembler",
        description="Bubble-free webtoon/PDF from Phase 5 panels + Story Library",
        phase="phase7.5",
        sort_order=75,
        status="in_progress",
        progress=0.05,
    )

    summaries = []
    try:
        for i, path in enumerate(paths):
            observer.set_progress(
                "phase7.5",
                0.1 + 0.8 * (i / max(len(paths), 1)),
                note=f"image_only {path.stem}",
            )
            episode = Episode.model_validate(json.loads(path.read_text()))
            man = assemble_episode(
                episode,
                story_id=path.stem,
                target_width=args.width,
                skip_existing=not args.no_skip,
                edition="image_only",
            )
            path.write_text(episode.model_dump_json(indent=2))
            summaries.append(
                {
                    "story_id": man["story_id"],
                    "status": man.get("status"),
                    "edition": "image_only",
                    "webtoon": man.get("webtoon_path"),
                    "pdf": man.get("pdf_path"),
                    "assembled": man.get("assembled_panels"),
                }
            )
            print(
                f"DONE {man['story_id']}: {man.get('status')} "
                f"image_only panels={man.get('assembled_panels')}"
            )

        out = OUTPUTS / "phase7.5" / "assemble_summary.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"stories": summaries}, indent=2))
        catalog = rebuild_catalog()
        observer.complete(
            "phase7.5",
            note=f"image_only {len(summaries)} stories; library={catalog['count']}",
        )
        print(f"summary → {out}")
        print(f"library → {catalog['store_path']} ({catalog['count']} stories)")
    except Exception as e:  # noqa: BLE001
        observer.fail("phase7.5", str(e))
        raise


if __name__ == "__main__":
    main()
