#!/usr/bin/env python3
"""Phase 1 (Mac): one Nano Banana image via Google API, fully cost-tracked.

Local FLUX.1-schnell runs on the Windows RTX 5060 Ti (CUDA 12.8) — see notebooks/phase1 notes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.clients import TrackedClients
from comicengine.config import OUTPUTS
from comicengine.style import build_prompt
from comicengine.tasks import observer


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--model",
        default="gemini-3.1-flash-image-preview",
        help="Flash image for cheap Phase1; use gemini-3-pro-image-preview for finals",
    )
    p.add_argument(
        "--prompt",
        default="A dad and young daughter reading a glowing history book under a bedside lamp",
    )
    args = p.parse_args()

    out = OUTPUTS / "phase1" / "nano_banana_hello.png"
    with observer.track("phase1", note="Nano Banana single image"):
        clients = TrackedClients(phase="phase1")
        prompt = build_prompt(args.prompt)
        path = clients.gemini_image(prompt, out_path=out, model=args.model, purpose="phase1_single")
    observer.refresh_from_world()
    print(f"saved {path}")
    print("Open dashboard: python scripts/run_dashboard.py")


if __name__ == "__main__":
    main()
