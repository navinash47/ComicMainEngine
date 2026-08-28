"""Identity vs beauty. grid_hist is log-only. B4 uses DINOv2/Gemini for Dad."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from skimage.transform import resize

from comicengine.v2b.eval.structure import EVAL_SIZE

CELLS = 8
LUMA_BINS = 32


def crop_index_channel(panel: Path, index_png: Path, *, channel: str = "R", pad: int = 8) -> Path:
    """Crop the panel to the object-index mask. channel R=dad, G=maya."""
    panel_im = Image.open(panel).convert("RGB")
    idx = Image.open(index_png).convert("RGB")
    if idx.size != panel_im.size:
        idx = idx.resize(panel_im.size)
    arr = np.asarray(idx)
    ch = {"R": 0, "G": 1, "B": 2}[channel]
    mask = arr[..., ch] > 40
    if not mask.any():
        raise RuntimeError(f"empty {channel} mask in {index_png}")
    ys, xs = np.where(mask)
    y0, y1 = max(0, int(ys.min()) - pad), min(arr.shape[0], int(ys.max()) + pad)
    x0, x1 = max(0, int(xs.min()) - pad), min(arr.shape[1], int(xs.max()) + pad)
    crop = panel_im.crop((x0, y0, x1, y1))
    dest = Path(panel).with_name(Path(panel).stem + f"_{channel.lower()}crop.png")
    crop.save(dest)
    return dest


def index_channel_mask(
    index_png: Path,
    *,
    channel: str = "G",
    dest: Path | None = None,
    threshold: int = 40,
) -> Path:
    """White-on-black RGB mask from an object-index channel (R=dad, G=maya)."""
    idx = Image.open(index_png).convert("RGB")
    arr = np.asarray(idx)
    ch = {"R": 0, "G": 1, "B": 2}[channel]
    mask = (arr[..., ch] > threshold).astype(np.uint8) * 255
    rgb = np.stack([mask, mask, mask], axis=-1)
    dest = Path(dest) if dest else Path(index_png).with_name(f"mask_{channel.lower()}.png")
    dest.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb).save(dest)
    return dest

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
        "note": "Cheap grid histogram. B4 identity uses DINOv2 in ComfyUI/.venv or Gemini same-person.",
    }
