#!/usr/bin/env python3
"""DINOv2 location similarity on B5 background crops. ComfyUI/.venv only."""

from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


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
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    import torch
    from transformers import AutoImageProcessor, AutoModel

    manifest = json.loads(Path(args.manifest).read_text())
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    processor = AutoImageProcessor.from_pretrained("facebook/dinov2-small")
    model = AutoModel.from_pretrained("facebook/dinov2-small").to(device)
    model.eval()

    groups: dict[str, list[tuple[str, np.ndarray]]] = {}
    for row in manifest.get("backgrounds") or []:
        path = Path(row["png"])
        if not path.is_file():
            continue
        vec = _embed(model, processor, path, device)
        groups.setdefault(str(row["location_id"]), []).append((str(path), vec))

    intra: dict[str, list[dict]] = {}
    intra_means: dict[str, float] = {}
    for loc, items in groups.items():
        pairs = []
        for (pa, va), (pb, vb) in combinations(items, 2):
            pairs.append({"a": pa, "b": pb, "cosine": round(cosine(va, vb), 4)})
        intra[loc] = pairs
        intra_means[loc] = round(sum(p["cosine"] for p in pairs) / len(pairs), 4) if pairs else None

    contrast = []
    living = groups.get("living_room") or []
    lobby = groups.get("grand_oriole_lobby") or []
    if living and lobby:
        mean_l = np.mean([v for _, v in living], axis=0)
        mean_h = np.mean([v for _, v in lobby], axis=0)
        contrast.append(
            {
                "a": "living_room",
                "b": "grand_oriole_lobby",
                "cosine": round(cosine(mean_l, mean_h), 4),
            }
        )
    living_mean = intra_means.get("living_room")
    lobby_mean = intra_means.get("grand_oriole_lobby")
    contrast_v = contrast[0]["cosine"] if contrast else None
    # Same-room should beat cross-room. Compass 0.9 is a hypothesis; not the gate.
    same_beats_cross = (
        living_mean is not None
        and lobby_mean is not None
        and contrast_v is not None
        and living_mean > contrast_v
        and lobby_mean > contrast_v
    )
    payload = {
        "method": "dinov2-small-background",
        "intra": intra,
        "intra_mean": intra_means,
        "contrast": contrast,
        "pass_same_beats_cross": bool(same_beats_cross),
        "note": "Compass named DINOv2(background) ≥ 0.9. B5 gate is same-location mean > cross-location. grid_hist is log-only.",
    }
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    return 0 if payload["pass_same_beats_cross"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
