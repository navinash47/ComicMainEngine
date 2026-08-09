#!/usr/bin/env python3
"""Phase 2 (Mac API slice): small style grid on Nano Banana v1 — tracks each image cost.

Default: 3 images (not 9) to keep spend low. Pass --count 9 for full 3x3.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.clients import TrackedClients
from comicengine.config import OUTPUTS
from comicengine.style import STYLE_SUFFIX, build_prompt
from comicengine.tasks import observer

SCENES = [
    "Dad lifting daughter onto his shoulders in a sunny meadow",
    "Dad and daughter peeking into an ancient library at dusk",
    "Daughter pointing at stars while Dad tells a gentle story",
    "Dad and daughter sharing cocoa beside a crackling fireplace",
    "Daughter sketching a historical monument while Dad smiles",
    "Dad and daughter walking a cobbled street lit by lanterns",
    "Daughter asleep holding a picture book; Dad tiptoeing out",
    "Dad and daughter watching ships in a painted harbor",
    "Daughter meeting a kindly historical figure in a soft dream",
]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=3, help="How many style samples (max 9)")
    p.add_argument("--model", default="gemini-3.1-flash-image-preview")
    args = p.parse_args()

    n = max(1, min(args.count, 9))
    clients = TrackedClients(phase="phase2")
    out_dir = OUTPUTS / "phase2"
    manifest = []

    observer.start("phase2", note=f"style grid x{n}")
    try:
        for i, scene in enumerate(SCENES[:n], start=1):
            prompt = build_prompt(scene, characters="recurring Dad and Daughter cast")
            path = out_dir / f"style_{i:02d}.png"
            clients.gemini_image(prompt, out_path=path, model=args.model, purpose="style_grid")
            manifest.append({"i": i, "scene": scene, "path": str(path), "style_suffix": STYLE_SUFFIX})
            observer.set_progress("phase2", i / n, note=f"{i}/{n} {path.name}")
            print(f"[{i}/{n}] {path.name}")

        man_path = out_dir / "style_manifest.json"
        man_path.write_text(json.dumps(manifest, indent=2))
        anchor = out_dir / "style_anchor.png"
        if (out_dir / "style_01.png").exists():
            anchor.write_bytes((out_dir / "style_01.png").read_bytes())
            print(f"provisional anchor -> {anchor}")
        print(f"manifest -> {man_path}")
        observer.complete("phase2", note=f"{n} style images")
    except Exception as e:  # noqa: BLE001
        observer.fail("phase2", str(e))
        raise
    finally:
        observer.refresh_from_world()


if __name__ == "__main__":
    main()
