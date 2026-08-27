"""HIMYM ep1 panel 1: Blender AOVs → ComfyUI (ControlNet when weights exist)."""

from __future__ import annotations

from pathlib import Path

from comicengine.config import OUTPUTS, ROOT
from comicengine.v2b.blender.run_headless import render_himym_p1, render_himym_p1_aovs
from comicengine.v2b.comfy.stylize import controlnet_weights_exist, stylize_controlnet, stylize_img2img
from comicengine.v2b.eval.structure import write_scorecard
from comicengine.v2b_program import EP01_PATH, load_program

DEFAULT_OUT = OUTPUTS / "v2b" / "himym_ep01" / "panel_01.png"
DEFAULT_DIR = OUTPUTS / "v2b" / "himym_ep01"
DEFAULT_SCORECARD = ROOT / "data" / "v2b" / "eval" / "himym_ep01_b2_structure.json"
CAMERAS = ("a", "b", "c")


def prove_paths() -> dict[str, Path]:
    program = load_program()
    prove = (program.get("ep01") or {}).get("b1_prove") or {}
    out = ROOT / prove["output"] if prove.get("output") else DEFAULT_OUT
    beauty = out.with_name("beauty_01.png")
    return {"beauty": beauty, "panel": out, "packet": EP01_PATH, "root": out.parent}


def run_b1(*, skip_comfy: bool = False) -> dict[str, str]:
    """B1 vertical slice: camera A beauty → optional img2img (no ControlNet)."""
    paths = prove_paths()
    beauty = render_himym_p1(paths["beauty"])
    result = {
        "beauty": str(beauty),
        "panel": None,
        "skipped_comfy": skip_comfy,
    }
    if skip_comfy:
        return result
    panel = stylize_img2img(beauty, paths["panel"])
    result["panel"] = str(panel)
    return result


def run_b2(
    *,
    skip_comfy: bool = False,
    cameras: tuple[str, ...] = CAMERAS,
    score: bool = True,
) -> dict[str, object]:
    root = DEFAULT_DIR
    cam_dirs = render_himym_p1_aovs(root, cameras=cameras)
    result: dict[str, object] = {
        "root": str(root),
        "cameras": {name: str(path) for name, path in cam_dirs.items()},
        "skipped_comfy": skip_comfy,
        "controlnet": controlnet_weights_exist(),
        "panels": {},
    }
    if skip_comfy:
        return result
    if not controlnet_weights_exist():
        raise FileNotFoundError(
            "B2 needs ControlNet weights in ComfyUI/models/controlnet/. "
            "See scripts/v2b_setup_local.sh"
        )
    panels: dict[str, str] = {}
    for name, cam_dir in cam_dirs.items():
        dest = cam_dir / "panel_01.png"
        stylize_controlnet(
            cam_dir / "beauty_01.png",
            cam_dir / "depth_01.png",
            cam_dir / "lineart_01.png",
            dest,
        )
        panels[name] = str(dest)
    result["panels"] = panels
    hero = Path(panels["a"])
    alias = root / "panel_01.png"
    alias.write_bytes(hero.read_bytes())
    result["panel"] = str(alias)
    if score:
        card = write_scorecard(root, DEFAULT_SCORECARD, cameras)
        result["scorecard"] = str(DEFAULT_SCORECARD)
        result["eval"] = card
    return result


def run_panel(*, skip_comfy: bool = False, b1: bool = False) -> dict[str, object]:
    if b1:
        return run_b1(skip_comfy=skip_comfy)
    return run_b2(skip_comfy=skip_comfy)
