#!/usr/bin/env python3
"""Romance Step 1 — lock feelings-forward HIMYM Episode 1 script (manhwa bible)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.config import OUTPUTS
from comicengine.romance_ep1 import build_episode
from comicengine.tasks import observer


def main() -> None:
    out_dir = OUTPUTS / "phase4"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "episode_how_i_met_your_mother_ep1.json"

    observer.upsert(
        "phase_romance_step1",
        title="Romance Step 1 — Infatuation script",
        description="Feelings-forward dad→daughter HIMYM Ep1 (butterflies, Maya teasing)",
        phase="phase_romance_step1",
        sort_order=200,
        status="in_progress",
        progress=0.1,
    )
    try:
        ep = build_episode()
        out_path.write_text(ep.model_dump_json(indent=2))
        romance_dir = OUTPUTS / "romance"
        romance_dir.mkdir(parents=True, exist_ok=True)
        (romance_dir / "step1_script_manifest.json").write_text(
            __import__("json").dumps(
                {
                    "path": str(out_path.relative_to(ROOT)),
                    "panels": len(ep.panels),
                    "title": ep.title,
                    "style": "korean_manhwa",
                },
                indent=2,
            )
        )
        observer.complete(
            "phase_romance_step1",
            note=f"{len(ep.panels)} panels → {out_path.name}",
        )
        print(f"saved {out_path}")
        print(f"panels {len(ep.panels)}")
        print(f"title {ep.title}")
    except Exception as e:  # noqa: BLE001
        observer.fail("phase_romance_step1", str(e))
        raise


if __name__ == "__main__":
    main()
