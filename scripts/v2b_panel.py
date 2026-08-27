#!/usr/bin/env python3
"""HIMYM ep1 panel 1 through Blender → ComfyUI.

B3 (ControlNet + locked style LoRA) is the default.
Pass --b2 for ControlNet without LoRA, --b1 for img2img-only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

from comicengine.v2b.pipeline.panel import run_panel  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--blender-only",
        action="store_true",
        help="Render Cycles AOVs and skip ComfyUI",
    )
    parser.add_argument(
        "--comfy-only",
        action="store_true",
        help="Reuse existing AOVs; skip Blender",
    )
    parser.add_argument(
        "--b1",
        action="store_true",
        help="B1 img2img only (no ControlNet, camera A beauty)",
    )
    parser.add_argument(
        "--b2",
        action="store_true",
        help="B2 ControlNet without style LoRA",
    )
    args = parser.parse_args()
    out = run_panel(
        skip_comfy=args.blender_only,
        skip_blender=args.comfy_only,
        b1=args.b1,
        b2=args.b2,
    )
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
