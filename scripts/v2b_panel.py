#!/usr/bin/env python3
"""HIMYM ep1 panel 1 through Blender → ComfyUI.

B2 (ControlNet) is the default when depth+lineart weights exist.
Pass --b1 for the img2img-only vertical slice.
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
        "--b1",
        action="store_true",
        help="B1 img2img only (no ControlNet, camera A beauty)",
    )
    args = parser.parse_args()
    out = run_panel(skip_comfy=args.blender_only, b1=args.b1)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
