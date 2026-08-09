#!/usr/bin/env python3
"""Romance Step 5 — assemble webtoon/PDF + refresh Library catalog."""

from __future__ import annotations

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

EPISODE = OUTPUTS / "phase4" / "episode_how_i_met_your_mother_ep1.json"


def main() -> None:
    if not EPISODE.is_file():
        raise SystemExit(f"missing {EPISODE}")
    observer.upsert(
        "phase_romance_step5",
        title="Romance Step 5 — Assemble + Library",
        description="Webtoon/PDF + catalog entry",
        phase="phase_romance_step5",
        sort_order=240,
        status="in_progress",
        progress=0.1,
    )
    try:
        episode = Episode.model_validate(json.loads(EPISODE.read_text()))
        man = assemble_episode(
            episode,
            story_id=EPISODE.stem,
            target_width=900,
            skip_existing=False,
        )
        EPISODE.write_text(episode.model_dump_json(indent=2))
        # image-only edition too if API supports
        try:
            man_img = assemble_episode(
                episode,
                story_id=EPISODE.stem,
                target_width=900,
                skip_existing=False,
                edition="image_only",
            )
        except TypeError:
            man_img = None
        catalog = rebuild_catalog()
        note = (
            f"webtoon={man.get('webtoon_path')} panels={man.get('assembled_panels')} "
            f"stories={len(catalog.get('stories') or [])}"
        )
        observer.complete("phase_romance_step5", note=note[:240])
        print("DONE", note)
        if man_img:
            print("image_only", man_img.get("webtoon_path") or man_img.get("status"))
    except Exception as e:  # noqa: BLE001
        observer.fail("phase_romance_step5", str(e))
        raise


if __name__ == "__main__":
    main()
