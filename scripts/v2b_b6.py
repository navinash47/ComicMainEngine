#!/usr/bin/env python3
"""Version 2B B6: Maya LoRA + two-pass object-index inpaint (living room cam_a, cam_c).

  PYTHONPATH=src python scripts/v2b_b6.py --all --quick
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
from comicengine.v2b.blender.run_headless import render_from_spec, render_turntable  # noqa: E402
from comicengine.v2b.comfy.stylize import stylize_controlnet, stylize_inpaint_controlnet  # noqa: E402
from comicengine.v2b.eval.identity import crop_index_channel, index_channel_mask  # noqa: E402
from comicengine.v2b.eval.select import evaluate_panel  # noqa: E402
from comicengine.v2b.eval.structure import STRUCTURE_FLOOR  # noqa: E402
from comicengine.v2b.lora.bootstrap import (  # noqa: E402
    B4_ROOT,
    stylize_character,
    write_character_metadata,
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
from comicengine.v2b.spec import LOCATIONS, load_b6_run  # noqa: E402

B6_ROOT = OUTPUTS / "v2b" / "himym_ep01" / "b6"
SCORECARD = CE_ROOT / "data" / "v2b" / "eval" / "himym_ep01_b6.json"
MAYA_META = CE_ROOT / "data" / "v2b" / "lora" / "maya" / "metadata.json"
COMFY_PY = CE_ROOT / "ComfyUI" / ".venv" / "bin" / "python"
TRAIN_PY = CE_ROOT / "scripts" / "v2b_b4_train.py"
DINO_PY = CE_ROOT / "scripts" / "v2b_b6_dino.py"
MAYA_LORA = CE_ROOT / "ComfyUI" / "models" / "loras" / "ce_maya.safetensors"
NEG = "photoreal, 3d render, cgi, watermark, text, letters, extra limbs, blurry, deformed"
MAYA_INPAINT_POS = (
    "ce_maya, indian teenage girl, oversized hoodie, ponytail, pajama pants, "
    "sitting on a sofa, storybook anime illustration, cel shaded comic panel, "
    "flat color, bold outlines, night living room, warm lamp, no text"
)
MAYA_INPAINT_NEG = (
    NEG + ", adult man, father, navy sweater, beard, curly hair, ce_dad_rohan"
)


def _cam_dir(cam: str) -> Path:
    return B6_ROOT / "living_room" / f"cam_{cam}"


def _turntable(quick: bool) -> dict[str, str]:
    existing = B4_ROOT / "turntable" / "maya"
    if (existing / "az000_el12" / "beauty_01.png").is_file():
        return {"maya": str(existing), "reused": "b4"}
    dest = B6_ROOT / "turntable" / "maya"
    return {"maya": str(render_turntable(dest, character="maya", quick=quick)), "reused": "none"}


def _bootstrap(quick: bool) -> dict[str, object]:
    turntable = B4_ROOT / "turntable" / "maya"
    if not (turntable / "az000_el12" / "beauty_01.png").is_file():
        turntable = B6_ROOT / "turntable" / "maya"
    dest = B6_ROOT / "dataset" / "maya"
    rows = stylize_character(
        "maya",
        quick=quick,
        dest_root=dest,
        turntable_root=turntable,
        full=True,
    )
    meta = write_character_metadata("maya", rows, MAYA_META)
    return {"metadata": str(meta), "n": len(rows), "train": sum(1 for r in rows if not r["holdout"])}


def _train(quick: bool) -> dict[str, object]:
    if not COMFY_PY.is_file():
        raise FileNotFoundError(f"ComfyUI venv missing: {COMFY_PY}")
    steps = 250 if quick else 800
    proc = subprocess.run(
        [
            str(COMFY_PY),
            str(TRAIN_PY),
            "--steps",
            str(steps),
            "--meta",
            str(MAYA_META),
            "--out",
            str(MAYA_LORA),
        ],
        cwd=str(CE_ROOT),
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"maya train failed with exit {proc.returncode}")
    digest = sha256_file(MAYA_LORA)
    upsert_character("maya", sha256=digest, trained=True, steps=steps, filename="ce_maya.safetensors")
    return {"lora": str(MAYA_LORA), "sha256": digest, "steps": steps}


def _render() -> dict[str, str]:
    run = load_b6_run()
    loc = LOCATIONS / f"{run.location_id}.json"
    dest = B6_ROOT / run.location_id
    cameras = tuple(run.cameras)
    chars = tuple(run.characters)
    print(f"render {run.location_id} cameras={cameras} chars={chars}", flush=True)
    paths = render_from_spec(loc, dest, cameras=cameras, characters=chars)
    return {k: str(v) for k, v in paths.items()}


def _panel() -> dict[str, object]:
    verify_style_lora()
    verify_character_lora("dad")
    verify_character_lora("maya")
    style = load_style()
    dad = load_character("dad")
    maya = load_character("maya")
    run = load_b6_run()
    dad_pos = f"{dad['trigger']}, {style['positive_prompt']}"
    panels: dict[str, object] = {}
    for cam in run.cameras:
        cam_dir = _cam_dir(cam)
        pass1 = cam_dir / "panel_01_pass1.png"
        final = cam_dir / "panel_01.png"
        mask = index_channel_mask(cam_dir / "index_01.png", channel="G", dest=cam_dir / "mask_g.png")
        print(f"pass1 {cam} exists={pass1.is_file()}", flush=True)
        if not pass1.is_file():
            stylize_controlnet(
                cam_dir / "beauty_01.png",
                cam_dir / "depth_01.png",
                cam_dir / "lineart_01.png",
                pass1,
                style_lora=True,
                character_lora=str(dad["filename"]),
                character_strength=float(dad.get("strength_model") or 0.8),
                positive=dad_pos,
            )
        print(f"pass2 {cam} exists={final.is_file()}", flush=True)
        if not final.is_file():
            stylize_inpaint_controlnet(
                pass1,
                cam_dir / "depth_01.png",
                cam_dir / "lineart_01.png",
                mask,
                final,
                character_lora=str(maya["filename"]),
                character_strength=float(maya.get("strength_model") or 0.8),
                denoise=0.55,
                positive=MAYA_INPAINT_POS,
                negative=MAYA_INPAINT_NEG,
                grow_mask_by=8,
            )
        panels[cam] = {"pass1": str(pass1), "panel": str(final), "mask": str(mask)}
    return panels


def _eval() -> dict[str, object]:
    run = load_b6_run()
    cameras: dict[str, object] = {}
    ssims: list[float] = []
    crops: list[dict[str, str]] = []
    for cam in run.cameras:
        cam_dir = _cam_dir(cam)
        panel = cam_dir / "panel_01.png"
        row = evaluate_panel(cam_dir, panel)
        try:
            dad_crop = crop_index_channel(panel, cam_dir / "index_01.png", channel="R")
            maya_crop = crop_index_channel(panel, cam_dir / "index_01.png", channel="G")
            pass1 = cam_dir / "panel_01_pass1.png"
            dad_pass1 = None
            maya_pass1 = None
            if pass1.is_file():
                dad_pass1 = str(crop_index_channel(pass1, cam_dir / "index_01.png", channel="R"))
                maya_pass1 = str(crop_index_channel(pass1, cam_dir / "index_01.png", channel="G"))
            row["dad_crop"] = str(dad_crop)
            row["maya_crop"] = str(maya_crop)
            crops.append(
                {
                    "camera": cam,
                    "dad_crop": str(dad_crop),
                    "maya_crop": str(maya_crop),
                    "dad_pass1": dad_pass1,
                    "maya_pass1": maya_pass1,
                }
            )
        except Exception as exc:
            row["crop_error"] = str(exc)
        cameras[f"cam_{cam}"] = row
        ssims.append(float(row["structure"]["ssim_depth"]))
    mean_ssim = round(sum(ssims) / len(ssims), 4) if ssims else None
    dino_out = CE_ROOT / "data" / "v2b" / "eval" / "himym_ep01_b6_dino.json"
    dino: dict[str, object] = {"method": "none", "pass_identity": False, "pass_bleed": False}
    if COMFY_PY.is_file():
        manifest = B6_ROOT / "bleed_manifest.json"
        manifest.write_text(json.dumps({"crops": crops}, indent=2) + "\n")
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
        "root": str(B6_ROOT),
        "structure_floor": STRUCTURE_FLOOR,
        "mean_ssim": mean_ssim,
        "pass_structure_floor": bool(mean_ssim is not None and mean_ssim >= STRUCTURE_FLOOR),
        "cameras": cameras,
        "identity_bleed": dino,
        "maya_lora": character_lora_exists("maya"),
            "note": (
                "Two-pass: style+Dad globally, then Maya LoRA inpainted on G-index. "
                "Maya holdout identity vs Dad sheet. Bleed: Dad R-crop stays close to pass1; "
                "Maya G-crop closer to Maya sheet than Dad. Seated dad_own vs Maya sheet is log-only "
                "(block meshes in a tight two-shot). Compass 0.85 not claimed. No InstantID. B8 stays locked."
            ),
    }
    SCORECARD.parent.mkdir(parents=True, exist_ok=True)
    SCORECARD.write_text(json.dumps(payload, indent=2) + "\n")
    payload["scorecard"] = str(SCORECARD)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--turntable", action="store_true")
    parser.add_argument("--bootstrap", action="store_true")
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--panel", action="store_true")
    parser.add_argument("--eval", action="store_true")
    args = parser.parse_args()
    if args.all:
        args.turntable = args.bootstrap = args.train = args.render = args.panel = args.eval = True
    if not any(
        [args.turntable, args.bootstrap, args.train, args.render, args.panel, args.eval]
    ):
        args.render = True
    out: dict[str, object] = {"root": str(B6_ROOT), "quick": args.quick}
    if args.turntable:
        out["turntable"] = _turntable(args.quick)
    if args.bootstrap:
        out["bootstrap"] = _bootstrap(args.quick)
    if args.train:
        out["train"] = _train(args.quick)
    if args.render:
        out["render"] = _render()
    if args.panel:
        out["panel"] = _panel()
    if args.eval:
        out["eval"] = _eval()
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
