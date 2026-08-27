"""Identity vs beauty. Capsules are not faces — log only, never a G1 fail gate.

Project venv has no torch. Use a spatial color grid (CLIP/DINOv2 stand-in).
B4 should replace this with real DINOv2/CLIP once torch is in the ComicEngine env.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from skimage.transform import resize

from comicengine.v2b.eval.structure import EVAL_SIZE

CELLS = 8
LUMA_BINS = 32


def _embed(path: Path) -> np.ndarray:
    arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    arr = resize(arr, (EVAL_SIZE[1], EVAL_SIZE[0], 3), anti_aliasing=True, preserve_range=True)
    h, w, _ = arr.shape
    tiles = []
    for i in range(CELLS):
        for j in range(CELLS):
            y0, y1 = int(i * h / CELLS), int((i + 1) * h / CELLS)
            x0, x1 = int(j * w / CELLS), int((j + 1) * w / CELLS)
            tiles.append(arr[y0:y1, x0:x1].mean(axis=(0, 1)))
    grid = np.concatenate(tiles)
    luma = (0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]).ravel()
    hist, _ = np.histogram(luma, bins=LUMA_BINS, range=(0.0, 1.0), density=True)
    vec = np.concatenate([grid, hist.astype(np.float32)])
    n = float(np.linalg.norm(vec))
    return vec / n if n > 1e-8 else vec


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def score_vs_beauty(panel: Path, beauty: Path) -> dict[str, Any]:
    """Log-only identity. Same embedding used as clip_cosine and dino_cosine aliases."""
    sim = round(cosine(_embed(Path(panel)), _embed(Path(beauty))), 4)
    return {
        "identity_cosine": sim,
        "clip_cosine": sim,
        "dino_cosine": sim,
        "method": "grid_hist_8x8",
        "note": "Not DINOv2/CLIP weights. Capsule-vs-capsule baseline until B4.",
    }
