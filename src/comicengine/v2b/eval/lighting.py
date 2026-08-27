"""Lighting vs the Cycles beauty pass. Histogram + left/right key-light polarity."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from skimage.transform import resize

from comicengine.v2b.eval.structure import EVAL_SIZE


def _luma(path: Path) -> np.ndarray:
    arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    arr = resize(arr, (EVAL_SIZE[1], EVAL_SIZE[0]), anti_aliasing=True, preserve_range=True)
    return (0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]).astype(np.float32)


def score_vs_beauty(panel: Path, beauty: Path) -> dict[str, Any]:
    p = _luma(Path(panel))
    b = _luma(Path(beauty))
    ph, _ = np.histogram(p, bins=32, range=(0.0, 1.0), density=True)
    bh, _ = np.histogram(b, bins=32, range=(0.0, 1.0), density=True)
    l1 = float(np.abs(ph - bh).mean())
    p_left, p_right = float(p[:, : p.shape[1] // 2].mean()), float(p[:, p.shape[1] // 2 :].mean())
    b_left, b_right = float(b[:, : b.shape[1] // 2].mean()), float(b[:, b.shape[1] // 2 :].mean())
    panel_left_brighter = p_left >= p_right
    beauty_left_brighter = b_left >= b_right
    return {
        "hist_l1": round(l1, 4),
        "panel_left_minus_right": round(p_left - p_right, 4),
        "beauty_left_minus_right": round(b_left - b_right, 4),
        "key_light_side_match": panel_left_brighter == beauty_left_brighter,
    }
