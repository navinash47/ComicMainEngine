#!/usr/bin/env python3
"""Phase 1: single-image generation — default FLUX.1 schnell via fal (tracked in analytics).

Also supports --backend gemini for Nano Banana (direct Google). Image APIs never use OmniRoute.
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
    p.add_argument("--backend", choices=("fal", "gemini"), default="fal")
    p.add_argument(
        "--model",
        default=None,
        help="fal: fal-ai/flux/schnell (default). gemini: gemini-3.1-flash-image-preview",
    )
    p.add_argument(
        "--prompt",
        default="A dad and young daughter reading a glowing history book under a bedside lamp",
    )
    p.add_argument("--seed", type=int, default=None)
    args = p.parse_args()

    clients = TrackedClients(phase="phase1")
    prompt = build_prompt(args.prompt)

    if args.backend == "fal":
        model = args.model or "fal-ai/flux/schnell"
        out = OUTPUTS / "phase1" / "flux_schnell_fal.png"
        with observer.track("phase1", note=f"FLUX schnell via fal ({model})"):
            path = clients.fal_flux_image(
                prompt,
                out_path=out,
                model=model,
                purpose="phase1_single",
                seed=args.seed,
            )
    else:
        model = args.model or "gemini-3.1-flash-image-preview"
        out = OUTPUTS / "phase1" / "nano_banana_hello.png"
        with observer.track("phase1", note=f"Nano Banana ({model})"):
            path = clients.gemini_image(prompt, out_path=out, model=model, purpose="phase1_single")

    observer.refresh_from_world()
    print(f"backend={args.backend} model={model}")
    print(f"saved {path}")
    print("Analytics: http://127.0.0.1:8765/analytics")


if __name__ == "__main__":
    main()
