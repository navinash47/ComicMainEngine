#!/usr/bin/env python3
"""Phase 6 — compose speech bubbles + captions onto Phase 5 panel images."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.compositor import compose_episode
from comicengine.config import OUTPUTS
from comicengine.episode_schema import Episode
from comicengine.tasks import observer

DEFAULT = [
    OUTPUTS / "phase0.5" / "episode_cjp_origin.json",
    OUTPUTS / "phase4" / "episode_et_tu_brutus.json",
    OUTPUTS / "phase4" / "episode_hitler_warning.json",
]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--stories", default="all")
    p.add_argument("--no-skip", action="store_true")
    args = p.parse_args()

    stem_map = {
        "all": DEFAULT,
        "cjp": [DEFAULT[0]],
        "episode_cjp_origin": [DEFAULT[0]],
        "et_tu_brutus": [DEFAULT[1]],
        "episode_et_tu_brutus": [DEFAULT[1]],
        "hitler_warning": [DEFAULT[2]],
        "episode_hitler_warning": [DEFAULT[2]],
    }
    if args.stories in stem_map:
        paths = stem_map[args.stories]
    else:
        paths = []
        for key in args.stories.split(","):
            key = key.strip()
            if key in stem_map and key != "all":
                paths.extend(stem_map[key])
            else:
                raise SystemExit(f"unknown story {key}")

    observer.upsert(
        "phase6",
        title="Phase 6 — Speech bubble compositor",
        description="Pillow captions/bubbles + story reader narration",
        phase="phase6",
        sort_order=60,
        status="in_progress",
        progress=0.05,
    )

    summaries = []
    try:
        for i, path in enumerate(paths):
            observer.set_progress("phase6", 0.1 + 0.8 * (i / max(len(paths), 1)), note=path.stem)
            episode = Episode.model_validate(json.loads(path.read_text()))
            man = compose_episode(
                episode,
                story_id=path.stem,
                skip_existing=not args.no_skip,
            )
            path.write_text(episode.model_dump_json(indent=2))
            summaries.append(
                {"story_id": man["story_id"], "ok": man["ok"], "errors": man["errors"]}
            )
            print(f"DONE {man['story_id']}: ok={man['ok']} err={man['errors']}")

        out = OUTPUTS / "phase6" / "compose_summary.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"stories": summaries}, indent=2))
        observer.complete("phase6", note=f"composed {summaries}")
        print(f"summary → {out}")
    except Exception as e:  # noqa: BLE001
        observer.fail("phase6", str(e))
        raise


if __name__ == "__main__":
    main()
