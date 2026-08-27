"""Hard gates then rank. Structure floor 0.53; restage vs beauty; identity is log-only."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from skimage.color import rgb2gray
from skimage.transform import resize

from comicengine.v2b.eval.identity import score_vs_beauty as identity_vs_beauty
from comicengine.v2b.eval.lighting import score_vs_beauty as lighting_vs_beauty
from comicengine.v2b.eval.structure import EVAL_SIZE, STRUCTURE_FLOOR, score_camera
from comicengine.v2b.eval.vlm_judge import pairwise
from comicengine.usage import UsageDB

RESTAGE_MAE_MAX = 0.12  # B1 restage was visual; B2/B3 vs beauty stayed well below this


def _mae(a: Path, b: Path) -> float:
    xa = np.asarray(Image.open(a).convert("RGB"), dtype=np.float32)
    xb = np.asarray(Image.open(b).convert("RGB"), dtype=np.float32)
    xb = np.asarray(
        Image.fromarray(xb.astype(np.uint8)).resize((xa.shape[1], xa.shape[0])),
        dtype=np.float32,
    )
    return float(np.abs(xa - xb).mean() / 255.0)


def _depth_corr(panel: Path, beauty: Path) -> float:
    def gray(path: Path) -> np.ndarray:
        arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
        g = rgb2gray(arr)
        return resize(g, (EVAL_SIZE[1], EVAL_SIZE[0]), anti_aliasing=True, preserve_range=True)

    p, b = gray(panel).ravel(), gray(beauty).ravel()
    if p.std() < 1e-6 or b.std() < 1e-6:
        return 0.0
    return float(np.corrcoef(p, b)[0, 1])


def restage_check(cam_dir: Path, panel: Path) -> dict[str, Any]:
    beauty = Path(cam_dir) / "beauty_01.png"
    mae = round(_mae(panel, beauty), 4)
    corr = round(_depth_corr(panel, beauty), 4)
    ok = mae <= RESTAGE_MAE_MAX and corr >= 0.35
    return {
        "ok": ok,
        "mae_vs_beauty": mae,
        "luma_corr_vs_beauty": corr,
        "mae_max": RESTAGE_MAE_MAX,
    }


def evaluate_panel(cam_dir: Path, panel: Path) -> dict[str, Any]:
    cam_dir, panel = Path(cam_dir), Path(panel)
    beauty = cam_dir / "beauty_01.png"
    structure = score_camera(cam_dir, panel)
    restage = restage_check(cam_dir, panel)
    identity = identity_vs_beauty(panel, beauty)
    lighting = lighting_vs_beauty(panel, beauty)
    hard_ok = bool(structure.get("pass_structure_floor")) and bool(restage.get("ok"))
    return {
        "panel": str(panel),
        "hard_ok": hard_ok,
        "structure": structure,
        "restage": restage,
        "identity": identity,
        "lighting": lighting,
    }


def rank_candidates(
    cam_dir: Path,
    panels: list[Path],
    *,
    db: UsageDB | None = None,
    judge: bool = True,
) -> dict[str, Any]:
    """Hard-gate then optional Gemini knockout. Identity cosine is a tie-break only."""
    scored = [evaluate_panel(cam_dir, Path(p)) for p in panels]
    survivors = [row for row in scored if row["hard_ok"]]
    if not survivors:
        survivors = scored
    ranked = sorted(
        survivors,
        key=lambda r: (
            float(r["structure"]["ssim_depth"]),
            float(r["identity"]["identity_cosine"]),
        ),
        reverse=True,
    )
    winner = Path(ranked[0]["panel"])
    tournament: list[dict[str, Any]] = []
    if judge and len(ranked) >= 2:
        db = db or UsageDB()
        contenders = [Path(r["panel"]) for r in ranked[:4]]
        while len(contenders) > 1:
            nxt: list[Path] = []
            i = 0
            while i < len(contenders):
                if i + 1 >= len(contenders):
                    nxt.append(contenders[i])
                    break
                a, b = contenders[i], contenders[i + 1]
                result = pairwise(a, b, db=db)
                pick = a if result["winner"] in {"A", "tie"} else b
                tournament.append(
                    {
                        "a": str(a),
                        "b": str(b),
                        "winner": result["winner"],
                        "picked": str(pick),
                        "axes": result["axes"],
                    }
                )
                nxt.append(pick)
                i += 2
            contenders = nxt
        winner = contenders[0]
    return {
        "camera": Path(cam_dir).name,
        "scored": scored,
        "winner": str(winner),
        "tournament": tournament,
        "structure_floor": STRUCTURE_FLOOR,
    }
