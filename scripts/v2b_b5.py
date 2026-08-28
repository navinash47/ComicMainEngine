#!/usr/bin/env python3
"""Version 2B B5: spec-driven location reuse (living room + Grand Oriole lobby).

  PYTHONPATH=src python scripts/v2b_b5.py --all
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

from comicengine.config import OUTPUTS, ROOT as CE_ROOT  # noqa: E402
from comicengine.v2b.blender.run_headless import render_from_spec  # noqa: E402
from comicengine.v2b.comfy.stylize import stylize_controlnet  # noqa: E402
from comicengine.v2b.eval.location import background_png, pair_cosine  # noqa: E402
from comicengine.v2b.eval.select import evaluate_panel  # noqa: E402
from comicengine.v2b.eval.structure import STRUCTURE_FLOOR  # noqa: E402
from comicengine.v2b.lora.registry import load_character, load_style, verify_character_lora, verify_style_lora  # noqa: E402
from comicengine.v2b.spec import LOCATIONS, load_b5_run, load_location  # noqa: E402

B5_ROOT = OUTPUTS / "v2b" / "himym_ep01" / "b5"
SCORECARD = CE_ROOT / "data" / "v2b" / "eval" / "himym_ep01_b5.json"
COMFY_PY = CE_ROOT / "ComfyUI" / ".venv" / "bin" / "python"
DINO_PY = CE_ROOT / "scripts" / "v2b_b5_dino.py"
NEG = "photoreal, 3d render, cgi, watermark, text, letters, extra limbs, blurry, deformed"


def _panel_dir(panel) -> Path:
    return B5_ROOT / panel.location_id / f"cam_{panel.camera}"


def _render() -> dict[str, object]:
    run = load_b5_run()
    grouped: dict[str, list] = defaultdict(list)
    for panel in run.panels:
        grouped[panel.location_id].append(panel)
    out: dict[str, object] = {}
    for loc_id, panels in grouped.items():
        loc_path = LOCATIONS / f"{loc_id}.json"
        load_location(loc_id)
        cameras = tuple(dict.fromkeys(p.camera for p in panels))
        chars = tuple(dict.fromkeys(c for p in panels for c in p.characters))
        dest = B5_ROOT / loc_id
        print(f"render {loc_id} cameras={cameras} chars={chars}", flush=True)
        paths = render_from_spec(loc_path, dest, cameras=cameras, characters=chars)
        out[loc_id] = {k: str(v) for k, v in paths.items()}
    return out


def _stylize() -> dict[str, str]:
    verify_style_lora()
    run = load_b5_run()
    style = load_style()
    dad = load_character("dad")
    panels: dict[str, str] = {}
    for panel in run.panels:
        cam_dir = _panel_dir(panel)
        dest = cam_dir / "panel_01.png"
        print(f"stylize {panel.id} exists={dest.is_file()}", flush=True)
        if dest.is_file():
            panels[panel.id] = str(dest)
            continue
        positive = panel.positive
        character_lora = None
        strength = 0.8
        if panel.character_lora:
            verify_character_lora(panel.character_lora)
            ch = load_character(panel.character_lora)
            character_lora = str(ch["filename"])
            strength = float(ch.get("strength_model") or 0.8)
            trigger = str(ch["trigger"])
            positive = positive or f"{trigger}, {style['positive_prompt']}"
        stylize_controlnet(
            cam_dir / "beauty_01.png",
            cam_dir / "depth_01.png",
            cam_dir / "lineart_01.png",
            dest,
            style_lora=True,
            seed=panel.seed,
            character_lora=character_lora,
            character_strength=strength,
            positive=positive,
            negative=NEG if panel.positive else None,
        )
        panels[panel.id] = str(dest)
    return panels


def _eval() -> dict[str, object]:
    run = load_b5_run()
    cameras: dict[str, object] = {}
    living_ssims: list[float] = []
    lobby_ssims: list[float] = []
    backgrounds: list[dict[str, str]] = []
    cheap_pairs: list[dict[str, object]] = []
    by_loc: dict[str, list[Path]] = defaultdict(list)
    for panel in run.panels:
        cam_dir = _panel_dir(panel)
        row = evaluate_panel(cam_dir, cam_dir / "panel_01.png")
        cameras[panel.id] = row
        ssim = float(row["structure"]["ssim_depth"])
        if panel.location_id == "living_room":
            living_ssims.append(ssim)
        else:
            lobby_ssims.append(ssim)
        bg = background_png(cam_dir / "panel_01.png", cam_dir / "index_01.png")
        backgrounds.append({"location_id": panel.location_id, "png": str(bg), "panel": panel.id})
        by_loc[panel.location_id].append(bg)
    mean_living = round(sum(living_ssims) / len(living_ssims), 4) if living_ssims else None
    mean_lobby = round(sum(lobby_ssims) / len(lobby_ssims), 4) if lobby_ssims else None
    mean_all = round(
        (sum(living_ssims) + sum(lobby_ssims)) / max(1, len(living_ssims) + len(lobby_ssims)),
        4,
    )
    for loc, paths in by_loc.items():
        for i, a in enumerate(paths):
            for b in paths[i + 1 :]:
                cheap_pairs.append({"location_id": loc, "a": str(a), "b": str(b), "grid_hist": pair_cosine(a, b)})
    dino_out = CE_ROOT / "data" / "v2b" / "eval" / "himym_ep01_b5_dino.json"
    dino: dict[str, object] = {"method": "none", "pass_same_beats_cross": False}
    if COMFY_PY.is_file():
        manifest = B5_ROOT / "location_manifest.json"
        manifest.write_text(json.dumps({"backgrounds": backgrounds}, indent=2) + "\n")
        proc = subprocess.run(
            [str(COMFY_PY), str(DINO_PY), "--manifest", str(manifest), "--out", str(dino_out)],
            cwd=str(CE_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        if dino_out.is_file():
            dino = json.loads(dino_out.read_text())
        else:
            dino["error"] = (proc.stderr or proc.stdout)[-800:]
    payload = {
        "root": str(B5_ROOT),
        "structure_floor": STRUCTURE_FLOOR,
        "mean_ssim_living": mean_living,
        "mean_ssim_lobby": mean_lobby,
        "mean_ssim_all": mean_all,
        "pass_structure_floor": bool(mean_living is not None and mean_living >= STRUCTURE_FLOOR),
        "cameras": cameras,
        "location_grid_hist": cheap_pairs,
        "location": dino,
        "note": "Location gate is same-room DINOv2 mean > cross-room. Structure floor 0.53 applies to living-room cameras (B2 calibration), not empty lobby. Compass 0.9 is a hypothesis. No Rohan/Elena LoRA. B8 stays locked.",
    }
    SCORECARD.parent.mkdir(parents=True, exist_ok=True)
    SCORECARD.write_text(json.dumps(payload, indent=2) + "\n")
    payload["scorecard"] = str(SCORECARD)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--stylize", action="store_true")
    parser.add_argument("--eval", action="store_true")
    args = parser.parse_args()
    if args.all:
        args.render = args.stylize = args.eval = True
    if not any([args.render, args.stylize, args.eval]):
        args.render = True
    out: dict[str, object] = {"root": str(B5_ROOT)}
    if args.render:
        out["render"] = _render()
    if args.stylize:
        out["stylize"] = _stylize()
    if args.eval:
        out["eval"] = _eval()
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
