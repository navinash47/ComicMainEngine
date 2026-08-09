#!/usr/bin/env python3
"""Prepare feedback-beta/ for Vercel: stories.json + panel/PDF copies."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.config import OUTPUTS, ROOT as CE_ROOT
from comicengine.public_catalog import write_vercel_manifest
from comicengine.stories import load_story

DEST = ROOT / "feedback-beta" / "public"
COMICS = DEST / "comics"


def main() -> None:
    man = write_vercel_manifest(DEST / "stories.json")
    copied = 0
    for s in man["stories"]:
        sid = s["id"]
        out = COMICS / sid
        out.mkdir(parents=True, exist_ok=True)
        # PDF + webtoon from phase7
        for src, name in (
            (OUTPUTS / "phase7" / sid / "episode.pdf", "episode.pdf"),
            (OUTPUTS / "phase7" / sid / "webtoon.png", "webtoon.png"),
        ):
            if src.is_file():
                shutil.copy2(src, out / name)
                copied += 1
        # panels from composed phase6, else raw phase5
        story = load_story(sid) or {}
        ep = story.get("episode") or {}
        for p in ep.get("panels") or []:
            idx = int(p.get("index") or 0)
            if not idx:
                continue
            candidates = [
                CE_ROOT / str(p.get("composed_image_path") or ""),
                CE_ROOT / str(p.get("image_path") or ""),
                OUTPUTS / "phase6" / sid / f"panel_{idx:02d}.png",
                OUTPUTS / "phase5" / sid / f"panel_{idx:02d}.png",
            ]
            dest = out / f"panel_{idx:02d}.png"
            for c in candidates:
                if c.is_file():
                    shutil.copy2(c, dest)
                    copied += 1
                    break
    print(json.dumps({"ok": True, "stories": man["count"], "files_copied": copied, "dest": str(DEST)}, indent=2))


if __name__ == "__main__":
    main()
