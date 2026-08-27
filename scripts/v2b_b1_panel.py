#!/usr/bin/env python3
"""B1: HIMYM ep1 panel 1 living-room two-shot through Blender → ComfyUI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

from comicengine.v2b.pipeline.panel import run_b1  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--blender-only",
        action="store_true",
        help="Render the Cycles beauty pass and skip ComfyUI",
    )
    args = parser.parse_args()
    out = run_b1(skip_comfy=args.blender_only)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
