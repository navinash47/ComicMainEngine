"""Location reuse: background crop vs other panels of the same room.

DINOv2 (ComfyUI venv) is primary. grid_hist_8x8 is log-only, like identity.
Do not claim Compass 0.9 without calibration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from comicengine.v2b.eval.identity import cosine, _embed


def background_png(panel: Path, index_png: Path | None) -> Path:
    """Fill character-index pixels with mean background so location embeds ignore people."""
    panel_im = Image.open(panel).convert("RGB")
    arr = np.asarray(panel_im).copy()
    if index_png and Path(index_png).is_file():
        idx = Image.open(index_png).convert("RGB")
        if idx.size != panel_im.size:
            idx = idx.resize(panel_im.size)
        mask = np.asarray(idx)
        char = (mask[..., 0] > 40) | (mask[..., 1] > 40)
        if char.any() and (~char).any():
            fill = arr[~char].mean(axis=0)
            arr[char] = fill
    dest = Path(panel).with_name(Path(panel).stem + "_bg.png")
    Image.fromarray(arr).save(dest)
    return dest


def pair_cosine(a: Path, b: Path) -> float:
    return round(cosine(_embed(a), _embed(b)), 4)
