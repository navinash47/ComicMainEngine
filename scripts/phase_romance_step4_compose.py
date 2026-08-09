#!/usr/bin/env python3
"""Romance Step 4 — compose speech bubbles/captions for HIMYM Ep1."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.compositor import compose_episode
from comicengine.config import OUTPUTS
from comicengine.episode_schema import Episode
from comicengine.tasks import observer

EPISODE = OUTPUTS / "phase4" / "episode_how_i_met_your_mother_ep1.json"


def main() -> None:
    if not EPISODE.is_file():
        raise SystemExit(f"missing {EPISODE}")
    observer.upsert(
        "phase_romance_step4",
        title="Romance Step 4 — Speech bubbles",
        description="Compose dialogue/captions on panels",
        phase="phase_romance_step4",
        sort_order=230,
        status="in_progress",
        progress=0.1,
    )
    try:
        episode = Episode.model_validate(json.loads(EPISODE.read_text()))
        man = compose_episode(episode, story_id=EPISODE.stem, skip_existing=False)
        EPISODE.write_text(episode.model_dump_json(indent=2))
        note = f"ok={man['ok']} err={man['errors']}"
        if man["errors"]:
            observer.set_progress("phase_romance_step4", 0.9, note=note)
        else:
            observer.complete("phase_romance_step4", note=note)
        print(f"DONE {man['story_id']}: {note}")
    except Exception as e:  # noqa: BLE001
        observer.fail("phase_romance_step4", str(e))
        raise


if __name__ == "__main__":
    main()
