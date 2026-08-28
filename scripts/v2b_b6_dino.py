#!/usr/bin/env python3
"""DINOv2 Maya holdout identity + panel bleed on index crops. ComfyUI/.venv only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DAD_META = ROOT / "data" / "v2b" / "lora" / "dad" / "metadata.json"
MAYA_META = ROOT / "data" / "v2b" / "lora" / "maya" / "metadata.json"


def _embed(model, processor, path: Path, device):
    import torch

    im = Image.open(path).convert("RGB")
    inputs = processor(images=im, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        vec = model(**inputs).last_hidden_state[:, 0]
        vec = torch.nn.functional.normalize(vec, dim=-1)
    return vec.squeeze(0).cpu().numpy()


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


def _sheet(meta: dict, n: int = 4) -> list[Path]:
    rows = list(meta.get("train") or [])
    return [Path(r["png"]) for r in rows if Path(r["png"]).is_file()][:n]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    import torch
    from transformers import AutoImageProcessor, AutoModel

    dad_meta = json.loads(DAD_META.read_text())
    maya_meta = json.loads(MAYA_META.read_text())
    dad_sheet = _sheet(dad_meta)
    maya_sheet = _sheet(maya_meta)
    holdout = [Path(r["png"]) for r in maya_meta.get("holdout") or [] if Path(r["png"]).is_file()]
    if len(dad_sheet) < 2 or len(maya_sheet) < 2 or len(holdout) < 2:
        raise SystemExit("need dad sheet, maya sheet, and maya holdout PNGs")

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    processor = AutoImageProcessor.from_pretrained("facebook/dinov2-small")
    model = AutoModel.from_pretrained("facebook/dinov2-small").to(device)
    model.eval()
    dad_vec = np.mean([_embed(model, processor, p, device) for p in dad_sheet], axis=0)
    maya_vec = np.mean([_embed(model, processor, p, device) for p in maya_sheet], axis=0)

    identity = []
    wins = 0
    for path in holdout:
        v = _embed(model, processor, path, device)
        own = cosine(v, maya_vec)
        other = cosine(v, dad_vec)
        ok = own > other
        wins += int(ok)
        identity.append({"png": str(path), "maya": round(own, 4), "dad": round(other, 4), "ok": ok})
    n = len(holdout)
    pass_identity = wins >= max(3, int(0.75 * n)) if n >= 4 else wins >= max(1, n - 1)

    manifest = json.loads(Path(args.manifest).read_text())
    bleed = []
    bleed_ok = 0
    dad_stable_floor = 0.90
    for row in manifest.get("crops") or []:
        dad_crop = Path(row["dad_crop"])
        maya_crop = Path(row["maya_crop"])
        if not dad_crop.is_file() or not maya_crop.is_file():
            bleed.append({"camera": row.get("camera"), "error": "missing crop"})
            continue
        dv = _embed(model, processor, dad_crop, device)
        mv = _embed(model, processor, maya_crop, device)
        dad_own = cosine(dv, dad_vec)
        dad_cross = cosine(dv, maya_vec)
        maya_own = cosine(mv, maya_vec)
        maya_cross = cosine(mv, dad_vec)
        dad_stable = None
        maya_changed = None
        if row.get("dad_pass1") and Path(row["dad_pass1"]).is_file():
            dad_stable = round(cosine(dv, _embed(model, processor, Path(row["dad_pass1"]), device)), 4)
        if row.get("maya_pass1") and Path(row["maya_pass1"]).is_file():
            maya_changed = round(cosine(mv, _embed(model, processor, Path(row["maya_pass1"]), device)), 4)
        maya_ok = maya_own > maya_cross
        stable_ok = dad_stable is not None and dad_stable >= dad_stable_floor
        ok = bool(maya_ok and stable_ok)
        bleed_ok += int(ok)
        bleed.append(
            {
                "camera": row.get("camera"),
                "dad_own": round(dad_own, 4),
                "dad_cross": round(dad_cross, 4),
                "maya_own": round(maya_own, 4),
                "maya_cross": round(maya_cross, 4),
                "dad_stable_vs_pass1": dad_stable,
                "maya_vs_pass1": maya_changed,
                "dad_stable_floor": dad_stable_floor,
                "sheet_dad_own_beats_cross": dad_own > dad_cross,
                "ok": ok,
            }
        )
    pass_bleed = bool(bleed) and bleed_ok == len(bleed)
    payload = {
        "method": "dinov2-small",
        "identity": {
            "n": n,
            "wins": wins,
            "pass": pass_identity,
            "details": identity,
            "note": "Maya holdout closer to Maya sheet than Dad. Compass 0.85 not claimed.",
        },
        "bleed": {
            "n": len(bleed),
            "wins": bleed_ok,
            "pass": pass_bleed,
            "details": bleed,
            "note": (
                "Maya G-crop closer to Maya sheet than Dad. Dad R-crop cosine vs pass1 >= 0.90 "
                "(mask held). Seated dad_own vs Maya sheet is log-only: block meshes in a tight two-shot."
            ),
        },
        "pass_identity": pass_identity,
        "pass_bleed": pass_bleed,
    }
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    return 0 if pass_identity and pass_bleed else 1


if __name__ == "__main__":
    raise SystemExit(main())
