"""Turntable stylize → captioned Dad dataset. Images live under outputs/ (gitignored)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from comicengine.config import OUTPUTS, ROOT
from comicengine.v2b.blender.turntable_views import view_specs
from comicengine.v2b.comfy.stylize import stylize_controlnet
from comicengine.v2b.lora.registry import load_character, load_style

B4_ROOT = OUTPUTS / "v2b" / "himym_ep01" / "b4"
META_PATH = ROOT / "data" / "v2b" / "lora" / "dad" / "metadata.json"
CAPTION_ROOT = ROOT / "data" / "v2b" / "lora" / "dad"
BOOTSTRAP_SEEDS = (42, 43)
DAD_PROMPT = (
    "ce_dad_rohan, indian man late 30s, curly hair greying at temples, navy sweater, "
    "storybook anime illustration, cel shaded comic character, standing turntable, "
    "plain grey floor, no sofa, no living room, no text"
)
MAYA_PROMPT = (
    "indian teen girl, oversized hoodie, ponytail, pajama pants, "
    "storybook anime illustration, cel shaded comic character, standing turntable, "
    "plain grey floor, no sofa, no text"
)
NEG = "photoreal, 3d render, cgi, watermark, text, letters, extra limbs, blurry, deformed, sofa, living room"


def _view_dir(character: str, view_id: str) -> Path:
    return B4_ROOT / "turntable" / character / view_id


def caption_for(character: str, view: dict[str, object]) -> str:
    base = DAD_PROMPT if character == "dad" else MAYA_PROMPT
    return f"{base}, azimuth {view['azimuth']} degrees, elevation {view['elevation']} degrees"


def stylize_character(
    character: str,
    *,
    quick: bool = False,
    seeds: tuple[int, ...] = BOOTSTRAP_SEEDS,
) -> list[dict[str, Any]]:
    style = load_style()
    trigger = load_character("dad")["trigger"] if character == "dad" else ""
    rows: list[dict[str, Any]] = []
    dest_root = B4_ROOT / "dataset" / character
    dest_root.mkdir(parents=True, exist_ok=True)
    if character == "dad":
        CAPTION_ROOT.mkdir(parents=True, exist_ok=True)
    views = view_specs(quick=quick)
    if character == "maya":
        views = [v for v in views if not v["holdout"]][:4]
        seeds = (seeds[0],)
    for view in views:
        src = _view_dir(character, str(view["id"]))
        beauty, depth, lineart = src / "beauty_01.png", src / "depth_01.png", src / "lineart_01.png"
        if not beauty.is_file():
            raise FileNotFoundError(f"missing turntable AOV {beauty}")
        prompt = caption_for(character, view)
        if trigger and trigger not in prompt:
            prompt = f"{trigger}, {prompt}"
        for seed in seeds:
            name = f"{view['id']}_s{seed}.png"
            dest = dest_root / name
            print(f"stylize {character} {name} exists={dest.is_file()}", flush=True)
            if not dest.is_file():
                stylize_controlnet(
                    beauty,
                    depth,
                    lineart,
                    dest,
                    style_lora=True,
                    seed=seed,
                    denoise=0.40,
                    depth_strength=0.55,
                    lineart_strength=0.45,
                    positive=prompt,
                    negative=NEG,
                )
            dest.with_suffix(".txt").write_text(prompt + "\n")
            if character == "dad":
                (CAPTION_ROOT / dest.with_suffix(".txt").name).write_text(prompt + "\n")
            rows.append(
                {
                    "character": character,
                    "view_id": view["id"],
                    "azimuth": view["azimuth"],
                    "elevation": view["elevation"],
                    "holdout": bool(view["holdout"]),
                    "seed": seed,
                    "png": str(dest),
                    "caption": prompt,
                    "style": style["filename"],
                }
            )
    return rows


def write_metadata(dad_rows: list[dict[str, Any]], maya_rows: list[dict[str, Any]]) -> Path:
    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "trigger": load_character("dad")["trigger"],
        "denoise": 0.40,
        "depth_strength": 0.55,
        "lineart_strength": 0.45,
        "seeds": list(BOOTSTRAP_SEEDS),
        "dad": dad_rows,
        "maya_contrast": maya_rows,
        "train": [r for r in dad_rows if not r["holdout"]],
        "holdout": [r for r in dad_rows if r["holdout"]],
    }
    META_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    return META_PATH


def load_metadata() -> dict[str, Any]:
    if not META_PATH.is_file():
        raise FileNotFoundError(META_PATH)
    return json.loads(META_PATH.read_text())
