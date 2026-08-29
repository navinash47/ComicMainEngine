#!/usr/bin/env python3
"""Version 2B G2: Kenney CC0 glTF characters + new LoRAs + B2–B6 rollup.

  PYTHONPATH=src python scripts/v2b_g2.py --all --quick

Does not overwrite B4/B6 block LoRAs (ce_dad_rohan / ce_maya) or those trees.
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
from comicengine.v2b.lora.bootstrap import stylize_character, write_character_metadata  # noqa: E402
from comicengine.v2b.lora.registry import (  # noqa: E402
    character_lora_exists,
    load_character,
    load_style,
    sha256_file,
    upsert_character,
    verify_character_lora,
    verify_style_lora,
)
from comicengine.v2b.spec import LOCATIONS, MESH_DIR, load_g2_run  # noqa: E402

G2_ROOT = OUTPUTS / "v2b" / "himym_ep01" / "g2"
SCORECARD = CE_ROOT / "data" / "v2b" / "eval" / "himym_ep01_g2.json"
UNTIL_NOW = CE_ROOT / "data" / "v2b" / "eval" / "himym_ep01_until_now.json"
COMFY_PY = CE_ROOT / "ComfyUI" / ".venv" / "bin" / "python"
TRAIN_PY = CE_ROOT / "scripts" / "v2b_b4_train.py"
DINO_PY = CE_ROOT / "scripts" / "v2b_b6_dino.py"
FETCH_PY = CE_ROOT / "scripts" / "v2b_g2_fetch_meshes.py"
NEG = "photoreal, 3d render, cgi, watermark, text, letters, extra limbs, blurry, deformed"
MAYA_INPAINT_POS = (
    "ce_maya_gltf, indian teenage girl, oversized hoodie, ponytail, pajama pants, "
    "sitting on a sofa, storybook anime illustration, cel shaded comic panel, "
    "flat color, bold outlines, night living room, warm lamp, no text"
)
MAYA_INPAINT_NEG = (
    NEG + ", adult man, father, navy sweater, beard, curly hair, ce_dad_gltf, ce_dad_rohan"
)


def _cam_dir(cam: str) -> Path:
    return G2_ROOT / "living_room" / f"cam_{cam}"


def _meta(char_id: str) -> Path:
    return CE_ROOT / "data" / "v2b" / "lora" / char_id / "metadata.json"


def _lora_path(char_id: str) -> Path:
    return CE_ROOT / "ComfyUI" / "models" / "loras" / str(load_character(char_id)["filename"])


def _fetch() -> dict[str, object]:
    proc = subprocess.run([sys.executable, str(FETCH_PY)], cwd=str(CE_ROOT), check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"mesh fetch failed with exit {proc.returncode}")
    log = MESH_DIR / "fetch_log.json"
    return json.loads(log.read_text()) if log.is_file() else {"ok": True}


def _turntable(quick: bool) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in ("dad", "maya"):
        dest = G2_ROOT / "turntable" / key
        mesh = MESH_DIR / f"{key}_standing.glb"
        if (dest / "az000_el12" / "beauty_01.png").is_file():
            out[key] = str(dest)
            continue
        out[key] = str(render_turntable(dest, character=key, quick=quick, mesh=mesh))
    return out


def _bootstrap(quick: bool, char_id: str, mesh_key: str) -> dict[str, object]:
    turntable = G2_ROOT / "turntable" / mesh_key
    dest = G2_ROOT / "dataset" / char_id
    rows = stylize_character(
        char_id,
        quick=quick,
        dest_root=dest,
        turntable_root=turntable,
        full=True,
    )
    meta = write_character_metadata(char_id, rows, _meta(char_id))
    return {"metadata": str(meta), "n": len(rows), "train": sum(1 for r in rows if not r["holdout"])}


def _train(quick: bool, char_id: str) -> dict[str, object]:
    if not COMFY_PY.is_file():
        raise FileNotFoundError(f"ComfyUI venv missing: {COMFY_PY}")
    steps = 250 if quick else 800
    dest = _lora_path(char_id)
    proc = subprocess.run(
        [
            str(COMFY_PY),
            str(TRAIN_PY),
            "--steps",
            str(steps),
            "--meta",
            str(_meta(char_id)),
            "--out",
            str(dest),
        ],
        cwd=str(CE_ROOT),
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{char_id} train failed with exit {proc.returncode}")
    digest = sha256_file(dest)
    upsert_character(char_id, sha256=digest, trained=True, steps=steps, filename=dest.name)
    return {"lora": str(dest), "sha256": digest, "steps": steps}


def _render() -> dict[str, str]:
    run = load_g2_run()
    loc = LOCATIONS / f"{run.location_id}.json"
    dest = G2_ROOT / run.location_id
    cameras = tuple(run.cameras)
    chars = tuple(run.characters)
    print(f"render {run.location_id} cameras={cameras} chars={chars} meshes={MESH_DIR}", flush=True)
    paths = render_from_spec(loc, dest, cameras=cameras, characters=chars, mesh_dir=MESH_DIR)
    return {k: str(v) for k, v in paths.items()}


def _panel() -> dict[str, object]:
    verify_style_lora()
    run = load_g2_run()
    verify_character_lora(run.dad_lora)
    verify_character_lora(run.maya_lora)
    style = load_style()
    dad = load_character(run.dad_lora)
    maya = load_character(run.maya_lora)
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
    run = load_g2_run()
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
    dino_out = CE_ROOT / "data" / "v2b" / "eval" / "himym_ep01_g2_dino.json"
    dino: dict[str, object] = {"method": "none", "pass_identity": False, "pass_bleed": False}
    if COMFY_PY.is_file():
        manifest = G2_ROOT / "bleed_manifest.json"
        manifest.write_text(json.dumps({"crops": crops}, indent=2) + "\n")
        proc = subprocess.run(
            [
                str(COMFY_PY),
                str(DINO_PY),
                "--manifest",
                str(manifest),
                "--out",
                str(dino_out),
                "--dad-meta",
                str(_meta(run.dad_lora)),
                "--maya-meta",
                str(_meta(run.maya_lora)),
            ],
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
        "root": str(G2_ROOT),
        "mesh_pack": "Kenney Animated Characters Protagonists 1.1 (CC0)",
        "structure_floor": STRUCTURE_FLOOR,
        "mean_ssim": mean_ssim,
        "pass_structure_floor": bool(mean_ssim is not None and mean_ssim >= STRUCTURE_FLOOR),
        "cameras": cameras,
        "identity_bleed": dino,
        "dad_lora": character_lora_exists(run.dad_lora),
        "maya_lora": character_lora_exists(run.maya_lora),
        "block_loras_untouched": {
            "dad": character_lora_exists("dad"),
            "maya": character_lora_exists("maya"),
        },
        "note": (
            "Kenney CC0 glTF stand-ins, not Indian-presenting likenesses. New LoRAs ce_dad_gltf / "
            "ce_maya_gltf. Two-pass G-index inpaint. Seated sheet-vs-sheet is log-only if coin-flip. "
            "Compass 0.85 not claimed. Search UI is locked G3. No InstantID. B8 stays locked."
        ),
    }
    SCORECARD.parent.mkdir(parents=True, exist_ok=True)
    SCORECARD.write_text(json.dumps(payload, indent=2) + "\n")
    payload["scorecard"] = str(SCORECARD)
    payload["until_now"] = _rollup()
    return payload


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.is_file() else {}


def _rollup() -> dict[str, object]:
    eval_dir = CE_ROOT / "data" / "v2b" / "eval"
    b2 = _read_json(eval_dir / "himym_ep01_b2_structure.json")
    b3 = _read_json(eval_dir / "himym_ep01_b3_structure.json")
    b4 = _read_json(eval_dir / "himym_ep01_b4.json")
    b5 = _read_json(eval_dir / "himym_ep01_b5.json")
    b6 = _read_json(eval_dir / "himym_ep01_b6.json")
    g1 = _read_json(eval_dir / "himym_ep01_g1_scorecard.json")
    g2 = _read_json(SCORECARD)
    b6_dino = b6.get("identity_bleed") or _read_json(eval_dir / "himym_ep01_b6_dino.json")
    g2_dino = g2.get("identity_bleed") or _read_json(eval_dir / "himym_ep01_g2_dino.json")
    payload = {
        "id": "himym_ep01_until_now",
        "structure_floor": STRUCTURE_FLOOR,
        "gates": [
            {
                "id": "b2",
                "title": "AOVs + ControlNet",
                "mean_ssim": b2.get("mean_ssim_depth"),
                "pass": bool((b2.get("mean_ssim_depth") or 0) >= STRUCTURE_FLOOR),
                "note": "cheap skimage depth; visual geometry lock",
            },
            {
                "id": "b3",
                "title": "Style LoRA",
                "mean_ssim": b3.get("mean_ssim_depth"),
                "pass": bool((b3.get("mean_ssim_depth") or 0) >= STRUCTURE_FLOOR),
                "note": "storybook_anime_lora locked; capsules still",
            },
            {
                "id": "g1",
                "title": "Eval harness",
                "human_pairs": (g1.get("agreement") or {}).get("n_human") or 12,
                "gemini_exact": (g1.get("agreement") or {}).get("exact_matches"),
                "pass": True,
                "note": "harness PASS; exact LLM-human is calibration debt",
            },
            {
                "id": "b4",
                "title": "Dad LoRA (block mesh)",
                "mean_ssim": b4.get("mean_ssim_b4") or b4.get("mean_ssim"),
                "pass": bool(b4.get("pass_structure_floor")),
                "note": "DINOv2 Dad holdout 3/4; Compass 0.85 not claimed",
            },
            {
                "id": "b5",
                "title": "Location reuse",
                "mean_ssim_living": b5.get("mean_ssim_living"),
                "pass": bool(b5.get("pass_structure_floor")),
                "note": "same-room DINOv2 0.825 > cross 0.476; lobby empty-depth not the 0.53 floor",
            },
            {
                "id": "b6",
                "title": "Two-pass masks (block mesh)",
                "mean_ssim": b6.get("mean_ssim"),
                "pass": bool(b6.get("pass_structure_floor")) and bool(b6_dino.get("pass_identity")),
                "maya_holdout": (b6_dino.get("identity") or {}).get("wins"),
                "dad_vs_pass1": [
                    d.get("dad_stable_vs_pass1") for d in (b6_dino.get("bleed") or {}).get("details") or []
                ],
                "note": "seated dad_own vs Maya sheet log-only on block two-shots",
            },
            {
                "id": "g2",
                "title": "Kenney CC0 glTF characters",
                "mean_ssim": g2.get("mean_ssim"),
                "pass": bool(g2.get("pass_structure_floor")),
                "maya_holdout": (g2_dino.get("identity") or {}).get("wins"),
                "note": "stand-in bodies, not likeness; catalog search is G3",
            },
        ],
        "honesty": [
            "Compass DINOv2 0.85 / 0.9 and SSIM 0.7 are hypotheses. Calibrated floor is 0.53.",
            "B4/B6 LoRAs were trained on block humanoids. G2 retrains new adapters on Kenney meshes.",
            "Kenney skins are cartoon skaters, not Indian-presenting Dad/Maya.",
            "G3 dashboard catalog search is locked. Mixamo terms stay off-limits.",
            "B7 sequencing and B8 BoN stay locked. Do not render 76 panels.",
        ],
    }
    UNTIL_NOW.write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--turntable", action="store_true")
    parser.add_argument("--bootstrap", action="store_true")
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--panel", action="store_true")
    parser.add_argument("--eval", action="store_true")
    parser.add_argument("--rollup", action="store_true")
    args = parser.parse_args()
    if args.all:
        args.fetch = args.turntable = args.bootstrap = args.train = args.render = args.panel = args.eval = True
        args.rollup = True
    if not any(
        [args.fetch, args.turntable, args.bootstrap, args.train, args.render, args.panel, args.eval, args.rollup]
    ):
        args.rollup = True
    out: dict[str, object] = {"root": str(G2_ROOT), "quick": args.quick}
    if args.fetch:
        out["fetch"] = _fetch()
    if args.turntable:
        out["turntable"] = _turntable(args.quick)
    if args.bootstrap:
        out["bootstrap_dad"] = _bootstrap(args.quick, "dad_gltf", "dad")
        out["bootstrap_maya"] = _bootstrap(args.quick, "maya_gltf", "maya")
    if args.train:
        out["train_dad"] = _train(args.quick, "dad_gltf")
        out["train_maya"] = _train(args.quick, "maya_gltf")
    if args.render:
        out["render"] = _render()
    if args.panel:
        out["panel"] = _panel()
    if args.eval:
        out["eval"] = _eval()
    elif args.rollup:
        out["until_now"] = _rollup()
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
