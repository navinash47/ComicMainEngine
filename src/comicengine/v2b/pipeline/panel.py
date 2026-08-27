"""HIMYM ep1 panel 1: Blender AOVs → ComfyUI (ControlNet + style LoRA)."""

from __future__ import annotations

from pathlib import Path

from comicengine.config import OUTPUTS, ROOT
from comicengine.v2b.blender.run_headless import render_himym_p1, render_himym_p1_aovs
from comicengine.v2b.comfy.stylize import controlnet_weights_exist, stylize_controlnet, stylize_img2img
from comicengine.v2b.eval.structure import write_scorecard
from comicengine.v2b.lora.registry import verify_style_lora
from comicengine.v2b_program import EP01_PATH, load_program

DEFAULT_OUT = OUTPUTS / "v2b" / "himym_ep01" / "panel_01.png"
DEFAULT_DIR = OUTPUTS / "v2b" / "himym_ep01"
DEFAULT_SCORECARD_B2 = ROOT / "data" / "v2b" / "eval" / "himym_ep01_b2_structure.json"
DEFAULT_SCORECARD_B3 = ROOT / "data" / "v2b" / "eval" / "himym_ep01_b3_structure.json"
CAMERAS = ("a", "b", "c")


def prove_paths() -> dict[str, Path]:
    program = load_program()
    prove = (program.get("ep01") or {}).get("b1_prove") or {}
    out = ROOT / prove["output"] if prove.get("output") else DEFAULT_OUT
    beauty = out.with_name("beauty_01.png")
    return {"beauty": beauty, "panel": out, "packet": EP01_PATH, "root": out.parent}


def _camera_dirs(root: Path, cameras: tuple[str, ...]) -> dict[str, Path]:
    dirs: dict[str, Path] = {}
    for name in cameras:
        cam_dir = root / f"cam_{name}"
        for needed in ("beauty_01.png", "depth_01.png", "lineart_01.png"):
            path = cam_dir / needed
            if not path.is_file():
                raise FileNotFoundError(
                    f"Missing AOV {path}. Render first (omit --comfy-only) or run B2."
                )
        dirs[name] = cam_dir
    return dirs


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
    skip_blender: bool = False,
    cameras: tuple[str, ...] = CAMERAS,
    score: bool = True,
    style_lora: bool = False,
    scorecard: Path | None = None,
) -> dict[str, object]:
    root = DEFAULT_DIR
    cam_dirs = _camera_dirs(root, cameras) if skip_blender else render_himym_p1_aovs(root, cameras=cameras)
    result: dict[str, object] = {
        "root": str(root),
        "cameras": {name: str(path) for name, path in cam_dirs.items()},
        "skipped_comfy": skip_comfy,
        "skipped_blender": skip_blender,
        "controlnet": controlnet_weights_exist(),
        "style_lora": style_lora,
        "panels": {},
    }
    if skip_comfy:
        return result
    if not controlnet_weights_exist():
        raise FileNotFoundError(
            "B2/B3 need ControlNet weights in ComfyUI/models/controlnet/. "
            "See scripts/v2b_setup_local.sh"
        )
    if style_lora:
        verify_style_lora()
    panels: dict[str, str] = {}
    for name, cam_dir in cam_dirs.items():
        dest = cam_dir / "panel_01.png"
        stylize_controlnet(
            cam_dir / "beauty_01.png",
            cam_dir / "depth_01.png",
            cam_dir / "lineart_01.png",
            dest,
            style_lora=style_lora,
        )
        panels[name] = str(dest)
    result["panels"] = panels
    hero = Path(panels["a"])
    alias = root / "panel_01.png"
    alias.write_bytes(hero.read_bytes())
    result["panel"] = str(alias)
    if score:
        dest_card = Path(scorecard) if scorecard else DEFAULT_SCORECARD_B2
        card = write_scorecard(root, dest_card, cameras)
        result["scorecard"] = str(dest_card)
        result["eval"] = card
    return result


def run_b3(
    *,
    skip_comfy: bool = False,
    skip_blender: bool = True,
    cameras: tuple[str, ...] = CAMERAS,
    score: bool = True,
) -> dict[str, object]:
    """B3: reuse B2 AOVs, apply locked style LoRA on every ControlNet stylize."""
    return run_b2(
        skip_comfy=skip_comfy,
        skip_blender=skip_blender,
        cameras=cameras,
        score=score,
        style_lora=True,
        scorecard=DEFAULT_SCORECARD_B3,
    )


def run_panel(
    *,
    skip_comfy: bool = False,
    skip_blender: bool = False,
    b1: bool = False,
    b2: bool = False,
) -> dict[str, object]:
    if b1:
        return run_b1(skip_comfy=skip_comfy)
    if b2:
        return run_b2(skip_comfy=skip_comfy, skip_blender=skip_blender)
    if skip_comfy:
        return run_b3(skip_comfy=True, skip_blender=False)
    return run_b3(skip_comfy=False, skip_blender=True)
