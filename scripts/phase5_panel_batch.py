#!/usr/bin/env python3
"""Phase 5 — generate full panel images for CJP + Caesar + Hitler episodes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.config import OUTPUTS
from comicengine.panel_batch import render_episode
from comicengine.tasks import observer

DEFAULT_STORIES = [
    OUTPUTS / "phase0.5" / "episode_cjp_origin.json",
    OUTPUTS / "phase4" / "episode_et_tu_brutus.json",
    OUTPUTS / "phase4" / "episode_hitler_warning.json",
]


def main() -> None:
    p = argparse.ArgumentParser(description="Phase 5 panel batch generator")
    p.add_argument(
        "--stories",
        default="all",
        help="Comma stems or 'all' (cjp+caesar+hitler)",
    )
    p.add_argument("--limit", type=int, default=None, help="Max panels per story (debug)")
    p.add_argument("--no-skip", action="store_true", help="Regenerate even if PNG exists")
    p.add_argument("--retries", type=int, default=2)
    args = p.parse_args()

    stem_map = {
        "episode_cjp_origin": DEFAULT_STORIES[0],
        "cjp": DEFAULT_STORIES[0],
        "episode_et_tu_brutus": DEFAULT_STORIES[1],
        "et_tu_brutus": DEFAULT_STORIES[1],
        "caesar": DEFAULT_STORIES[1],
        "episode_hitler_warning": DEFAULT_STORIES[2],
        "hitler_warning": DEFAULT_STORIES[2],
        "hitler": DEFAULT_STORIES[2],
    }
    if args.stories.strip() == "all":
        paths = list(DEFAULT_STORIES)
    else:
        paths = []
        for key in args.stories.split(","):
            key = key.strip()
            if key in stem_map:
                paths.append(stem_map[key])
            else:
                cand = Path(key)
                if not cand.is_file():
                    raise SystemExit(f"unknown story {key}")
                paths.append(cand)

    for path in paths:
        if not path.is_file():
            raise SystemExit(f"missing episode JSON: {path}")

    observer.upsert(
        "phase5",
        title="Phase 5 — Panel batch generator",
        description="Episode JSON → panels (gemini_ref + retries)",
        phase="phase5",
        sort_order=50,
        status="in_progress",
        progress=0.05,
        meta={"stories": [p.name for p in paths]},
    )

    summaries: list[dict] = []
    try:
        for i, path in enumerate(paths):
            observer.set_progress(
                "phase5",
                0.1 + 0.8 * (i / max(len(paths), 1)),
                note=f"rendering {path.stem}…",
            )
            man = render_episode(
                path,
                skip_existing=not args.no_skip,
                panel_limit=args.limit,
                max_retries=args.retries,
            )
            summaries.append(
                {
                    "story_id": man["story_id"],
                    "ok": man["ok"],
                    "errors": man["errors"],
                    "panel_count": man["panel_count"],
                }
            )
            print(
                f"DONE {man['story_id']}: ok={man['ok']}/{man['panel_count']} "
                f"errors={man['errors']}"
            )

        out = OUTPUTS / "phase5" / "batch_summary.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"stories": summaries}, indent=2))
        total_ok = sum(s["ok"] for s in summaries)
        total = sum(s["panel_count"] for s in summaries)
        total_err = sum(s["errors"] for s in summaries)
        observer.complete(
            "phase5",
            note=f"panels ok={total_ok}/{total} errors={total_err} → {out}",
        )
        print(f"summary → {out}")
    except Exception as e:  # noqa: BLE001
        observer.fail("phase5", str(e))
        raise


if __name__ == "__main__":
    main()
