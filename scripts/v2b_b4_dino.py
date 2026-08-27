#!/usr/bin/env python3
"""DINOv2 cosine on Dad holdout vs Dad sheet vs Maya contrast. ComfyUI/.venv only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "data" / "v2b" / "lora" / "dad" / "metadata.json"


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    import torch
    from transformers import AutoImageProcessor, AutoModel

    meta = json.loads(META.read_text())
    holdout = [Path(r["png"]) for r in meta.get("holdout") or [] if Path(r["png"]).is_file()]
    train = [Path(r["png"]) for r in meta.get("train") or [] if Path(r["png"]).is_file()]
    maya = [Path(r["png"]) for r in meta.get("maya_contrast") or [] if Path(r["png"]).is_file()]
    if len(holdout) < 2 or len(train) < 2:
        raise SystemExit("need holdout and train stylized PNGs")
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    processor = AutoImageProcessor.from_pretrained("facebook/dinov2-small")
    model = AutoModel.from_pretrained("facebook/dinov2-small").to(device)
    model.eval()
    sheet = train[:4]
    sheet_vec = np.mean([_embed(model, processor, p, device) for p in sheet], axis=0)
    maya_vec = (
        np.mean([_embed(model, processor, p, device) for p in maya[:4]], axis=0) if maya else None
    )
    details = []
    wins = 0
    for path in holdout:
        v = _embed(model, processor, path, device)
        dad_c = cosine(v, sheet_vec)
        maya_c = cosine(v, maya_vec) if maya_vec is not None else -1.0
        ok = dad_c > maya_c
        wins += int(ok)
        details.append({"png": str(path), "dad": round(dad_c, 4), "maya": round(maya_c, 4), "ok": ok})
    n = len(holdout)
    payload = {
        "method": "dinov2-small",
        "n": n,
        "wins": wins,
        "pass": wins >= max(3, int(0.75 * n)),
        "details": details,
    }
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
