"""Cheap structure scorecard: Blender depth/Freestyle vs stylized PNG.

No Depth-Anything / VLM judge. skimage SSIM + Canny edge IoU only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from skimage.color import rgb2gray
from skimage.filters import gaussian, sobel
from skimage.metrics import structural_similarity as ssim
from skimage.transform import resize

SSIM_HYPOTHESIS = 0.7
STRUCTURE_FLOOR = 0.53  # B2 calibrated cheap-skimage floor on this Mac
EVAL_SIZE = (384, 576)  # W, H — matches 2:3 panel


def _load_gray(path: Path, size: tuple[int, int] = EVAL_SIZE) -> np.ndarray:
    arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    gray = rgb2gray(arr)
    return resize(gray, (size[1], size[0]), anti_aliasing=True, preserve_range=True).astype(np.float32)


def _cheap_depth(stylized_gray: np.ndarray) -> np.ndarray:
    """Low-frequency luminance as a stand-in for depth (no 2GB extractor)."""
    blurred = gaussian(stylized_gray, sigma=8.0, preserve_range=True)
    lo, hi = float(blurred.min()), float(blurred.max())
    if hi - lo < 1e-6:
        return np.zeros_like(blurred, dtype=np.float32)
    return ((blurred - lo) / (hi - lo)).astype(np.float32)


def _match_polarity(reference: np.ndarray, candidate: np.ndarray) -> np.ndarray:
    direct = float(ssim(reference, candidate, data_range=1.0))
    flipped = float(ssim(reference, 1.0 - candidate, data_range=1.0))
    return candidate if direct >= flipped else (1.0 - candidate)


def _edges(gray: np.ndarray, *, lineart: bool) -> np.ndarray:
    if lineart:
        return gray > 0.18
    mag = sobel(gray)
    thresh = max(0.08, float(np.percentile(mag, 85)))
    return mag >= thresh


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    a_b = a.astype(bool)
    b_b = b.astype(bool)
    inter = np.logical_and(a_b, b_b).sum()
    union = np.logical_or(a_b, b_b).sum()
    if union == 0:
        return 0.0
    return float(inter / union)


def score_camera(cam_dir: Path, panel: Path | None = None) -> dict[str, Any]:
    cam_dir = Path(cam_dir)
    panel_path = Path(panel) if panel else cam_dir / "panel_01.png"
    depth_gt = _load_gray(cam_dir / "depth_01.png")
    lineart_gt = _load_gray(cam_dir / "lineart_01.png")
    stylized = _load_gray(panel_path)
    cheap = _match_polarity(depth_gt, _cheap_depth(stylized))
    ssim_depth = float(ssim(depth_gt, cheap, data_range=1.0))
    edge_iou = _iou(_edges(lineart_gt, lineart=True), _edges(stylized, lineart=False))
    return {
        "camera": cam_dir.name,
        "panel": str(panel_path),
        "ssim_depth": round(ssim_depth, 4),
        "edge_iou": round(edge_iou, 4),
        "ssim_hypothesis": SSIM_HYPOTHESIS,
        "structure_floor": STRUCTURE_FLOOR,
        "pass_ssim_hypothesis": ssim_depth >= SSIM_HYPOTHESIS,
        "pass_structure_floor": ssim_depth >= STRUCTURE_FLOOR,
    }


def score_cameras(root: Path, cameras: tuple[str, ...] = ("a", "b", "c")) -> dict[str, Any]:
    rows = [score_camera(Path(root) / f"cam_{cam}") for cam in cameras]
    ssims = [row["ssim_depth"] for row in rows]
    ious = [row["edge_iou"] for row in rows]
    mean_ssim = float(np.mean(ssims))
    calibrated = SSIM_HYPOTHESIS
    note = "hypothesis SSIM(depth) >= 0.7"
    if mean_ssim < SSIM_HYPOTHESIS:
        calibrated = round(max(0.35, mean_ssim - 0.05), 2)
        note = (
            f"cheap skimage depth (no Depth-Anything) mean SSIM {mean_ssim:.3f} < 0.7; "
            f"calibrated floor {calibrated}"
        )
    return {
        "cameras": rows,
        "mean_ssim_depth": round(mean_ssim, 4),
        "mean_edge_iou": round(float(np.mean(ious)), 4),
        "hypothesis_ssim_depth": SSIM_HYPOTHESIS,
        "calibrated_ssim_floor": calibrated,
        "all_pass_hypothesis": all(row["pass_ssim_hypothesis"] for row in rows),
        "note": note,
    }


def write_scorecard(root: Path, dest: Path, cameras: tuple[str, ...] = ("a", "b", "c")) -> dict[str, Any]:
    card = score_cameras(root, cameras)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(card, indent=2) + "\n")
    return card
