#!/usr/bin/env python3
"""Version 2B B4: block meshes, Dad turntable LoRA, stacked infer, identity eval.

  PYTHONPATH=src python scripts/v2b_b4.py --meshes
  PYTHONPATH=src python scripts/v2b_b4.py --turntable --bootstrap --train --panel --eval
  PYTHONPATH=src python scripts/v2b_b4.py --all --quick
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

from comicengine.config import OUTPUTS, ROOT as CE_ROOT  # noqa: E402
from comicengine.usage import UsageDB  # noqa: E402
from comicengine.v2b.blender.run_headless import render_himym_p1_aovs, render_turntable  # noqa: E402
from comicengine.v2b.comfy.stylize import stylize_controlnet  # noqa: E402
from comicengine.v2b.eval.identity import crop_index_channel, score_vs_beauty  # noqa: E402
from comicengine.v2b.eval.select import evaluate_panel  # noqa: E402
from comicengine.v2b.eval.structure import STRUCTURE_FLOOR  # noqa: E402
from comicengine.v2b.eval.vlm_judge import same_person  # noqa: E402
from comicengine.v2b.lora.bootstrap import (  # noqa: E402
    B4_ROOT,
    META_PATH,
    load_metadata,
    stylize_character,
    write_metadata,
)
from comicengine.v2b.lora.registry import (  # noqa: E402
    character_lora_exists,
    load_character,
    load_style,
    sha256_file,
    upsert_character,
    verify_character_lora,
    verify_style_lora,
)

CAMERAS = ("a", "b", "c")
SCORECARD = CE_ROOT / "data" / "v2b" / "eval" / "himym_ep01_b4.json"
COMFY_PY = CE_ROOT / "ComfyUI" / ".venv" / "bin" / "python"
TRAIN_PY = CE_ROOT / "scripts" / "v2b_b4_train.py"
DINO_PY = CE_ROOT / "scripts" / "v2b_b4_dino.py"


def _meshes() -> dict[str, str]:
    paths = render_himym_p1_aovs(B4_ROOT, cameras=CAMERAS)
    return {k: str(v) for k, v in paths.items()}


def _turntable(quick: bool, maya: bool) -> dict[str, str]:
    dad = render_turntable(B4_ROOT / "turntable" / "dad", character="dad", quick=quick)
    out = {"dad": str(dad)}
    if maya:
        out["maya"] = str(render_turntable(B4_ROOT / "turntable" / "maya", character="maya", quick=True))
    return out


def _bootstrap(quick: bool, maya: bool) -> dict[str, object]:
    dad_rows = stylize_character("dad", quick=quick)
    write_metadata(dad_rows, [])
    maya_rows: list = []
    if maya and (B4_ROOT / "turntable" / "maya").is_dir():
        maya_rows = stylize_character("maya", quick=True)
    meta = write_metadata(dad_rows, maya_rows)
    return {"metadata": str(meta), "n_dad": len(dad_rows), "n_maya": len(maya_rows)}


def _train(quick: bool) -> dict[str, object]:
    if not COMFY_PY.is_file():
        raise FileNotFoundError(f"ComfyUI venv missing: {COMFY_PY}")
    steps = 250 if quick else 800
    proc = subprocess.run(
        [str(COMFY_PY), str(TRAIN_PY), "--steps", str(steps)],
        cwd=str(CE_ROOT),
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"train failed with exit {proc.returncode}")
    dest = CE_ROOT / "ComfyUI" / "models" / "loras" / "ce_dad_rohan.safetensors"
    digest = sha256_file(dest)
    upsert_character("dad", sha256=digest, trained=True, steps=steps)
    return {"lora": str(dest), "sha256": digest, "steps": steps}


def _panel() -> dict[str, object]:
    verify_style_lora()
    verify_character_lora("dad")
    style = load_style()
    dad = load_character("dad")
    positive = f"{dad['trigger']}, {style['positive_prompt']}"
    panels: dict[str, str] = {}
    for cam in CAMERAS:
        cam_dir = B4_ROOT / f"cam_{cam}"
        dest = cam_dir / "panel_01.png"
        stylize_controlnet(
            cam_dir / "beauty_01.png",
            cam_dir / "depth_01.png",
            cam_dir / "lineart_01.png",
            dest,
            style_lora=True,
            character_lora=str(dad["filename"]),
            character_strength=float(dad.get("strength_model") or 0.8),
            positive=positive,
        )
        panels[cam] = str(dest)
    return {"panels": panels}


def _identity(db: UsageDB) -> dict[str, object]:
    dino_out = CE_ROOT / "data" / "v2b" / "eval" / "himym_ep01_b4_dino.json"
    if COMFY_PY.is_file():
        proc = subprocess.run(
            [str(COMFY_PY), str(DINO_PY), "--out", str(dino_out)],
            cwd=str(CE_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode in {0, 1} and dino_out.is_file():
            payload = json.loads(dino_out.read_text())
            payload["fallback"] = None
            return payload
        dino_err = proc.stderr[-800:]
    else:
        dino_err = "no ComfyUI python"
    meta = load_metadata()
    holdout = [Path(r["png"]) for r in meta.get("holdout") or [] if Path(r["png"]).is_file()]
    sheet = [Path(r["png"]) for r in meta.get("train") or [] if Path(r["png"]).is_file()][:1]
    if not holdout or not sheet:
        return {"method": "none", "pass": False, "error": "missing dataset", "dino_err": dino_err}
    details = []
    wins = 0
    for path in holdout:
        row = same_person(sheet[0], path, db=db)
        wins += int(bool(row["same"]))
        details.append({"png": str(path), "same": row["same"], "reason": row.get("reason")})
    n = len(holdout)
    return {
        "method": "gemini-same-person",
        "n": n,
        "wins": wins,
        "pass": wins >= max(3, int(0.75 * n)) if n >= 4 else wins >= max(1, n - 1),
        "details": details,
        "dino_err": dino_err,
    }


def _eval() -> dict[str, object]:
    db = UsageDB()
    cameras = {}
    ssims = []
    for cam in CAMERAS:
        cam_dir = B4_ROOT / f"cam_{cam}"
        panel = cam_dir / "panel_01.png"
        row = evaluate_panel(cam_dir, panel)
        try:
            dad_crop = crop_index_channel(panel, cam_dir / "index_01.png", channel="R")
            row["dad_crop"] = str(dad_crop)
            row["dad_crop_vs_beauty"] = score_vs_beauty(dad_crop, cam_dir / "beauty_01.png")
        except Exception as exc:
            row["dad_crop_error"] = str(exc)
        cameras[f"cam_{cam}"] = row
        ssims.append(float(row["structure"]["ssim_depth"]))
    mean_ssim = round(sum(ssims) / len(ssims), 4) if ssims else None
    identity = _identity(db)
    payload = {
        "root": str(B4_ROOT),
        "structure_floor": STRUCTURE_FLOOR,
        "mean_ssim_b4": mean_ssim,
        "pass_structure_floor": bool(mean_ssim is not None and mean_ssim >= STRUCTURE_FLOOR),
        "cameras": cameras,
        "identity": identity,
        "character_lora": character_lora_exists("dad"),
        "metadata": str(META_PATH) if META_PATH.is_file() else None,
        "note": "Identity gate is Dad holdout closer to Dad sheet than Maya (DINOv2) or Gemini same-person 6/8. grid_hist is log-only.",
    }
    SCORECARD.parent.mkdir(parents=True, exist_ok=True)
    SCORECARD.write_text(json.dumps(payload, indent=2) + "\n")
    payload["scorecard"] = str(SCORECARD)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--meshes", action="store_true")
    parser.add_argument("--turntable", action="store_true")
    parser.add_argument("--bootstrap", action="store_true")
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--panel", action="store_true")
    parser.add_argument("--eval", action="store_true")
    parser.add_argument("--no-maya", action="store_true")
    args = parser.parse_args()
    if args.all:
        args.meshes = args.turntable = args.bootstrap = args.train = args.panel = args.eval = True
    if not any([args.meshes, args.turntable, args.bootstrap, args.train, args.panel, args.eval]):
        args.meshes = True
    maya = not args.no_maya
    out: dict[str, object] = {"root": str(B4_ROOT), "quick": args.quick}
    if args.meshes:
        out["meshes"] = _meshes()
    if args.turntable:
        out["turntable"] = _turntable(args.quick, maya)
    if args.bootstrap:
        out["bootstrap"] = _bootstrap(args.quick, maya)
    if args.train:
        out["train"] = _train(args.quick)
    if args.panel:
        out["panel"] = _panel()
    if args.eval:
        out["eval"] = _eval()
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
