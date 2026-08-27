"""B1 vertical slice: HIMYM ep1 panel 1 → Blender → ComfyUI PNG."""

from __future__ import annotations

from pathlib import Path

from comicengine.config import OUTPUTS, ROOT
from comicengine.v2b.blender.run_headless import render_himym_p1
from comicengine.v2b.comfy.stylize import stylize_img2img
from comicengine.v2b_program import EP01_PATH, load_program

DEFAULT_OUT = OUTPUTS / "v2b" / "himym_ep01" / "panel_01.png"
DEFAULT_BEAUTY = OUTPUTS / "v2b" / "himym_ep01" / "beauty_01.png"


def prove_paths() -> dict[str, Path]:
    program = load_program()
    prove = (program.get("ep01") or {}).get("b1_prove") or {}
    out = ROOT / prove["output"] if prove.get("output") else DEFAULT_OUT
    beauty = out.with_name("beauty_01.png")
    return {"beauty": beauty, "panel": out, "packet": EP01_PATH}


def run_b1(*, skip_comfy: bool = False) -> dict[str, str]:
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
