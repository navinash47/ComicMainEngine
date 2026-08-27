#!/usr/bin/env python3
"""Version 2B Gate 1: score B1/B2/B3, optional B1 restore, BoN, Gemini pairwise.

  PYTHONPATH=src python scripts/v2b_gate1.py --all
  PYTHONPATH=src python scripts/v2b_gate1.py --score
  PYTHONPATH=src python scripts/v2b_gate1.py --b1
  PYTHONPATH=src python scripts/v2b_gate1.py --bon
  PYTHONPATH=src python scripts/v2b_gate1.py --judge
  PYTHONPATH=src python scripts/v2b_gate1.py --agreement
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

from comicengine.config import OUTPUTS, ROOT as CE_ROOT  # noqa: E402
from comicengine.usage import UsageDB  # noqa: E402
from comicengine.v2b.comfy.stylize import stylize_controlnet, stylize_img2img  # noqa: E402
from comicengine.v2b.eval.preferences import (  # noqa: E402
    PAIRS,
    PREFS_PATH,
    agreement,
    append_pref,
    latest_by_pair,
    pair_catalog,
    resolve_slot,
)
from comicengine.v2b.eval.select import evaluate_panel, rank_candidates  # noqa: E402
from comicengine.v2b.eval.vlm_judge import pairwise  # noqa: E402

OUT = OUTPUTS / "v2b" / "himym_ep01"
SCORECARD = CE_ROOT / "data" / "v2b" / "eval" / "himym_ep01_g1_scorecard.json"
CAMERAS = ("a", "b", "c")
BON_SEEDS = (42, 43, 44, 45)


def _restore_b1() -> Path:
    dest = OUT / "cam_a" / "panel_01_b1.png"
    if dest.is_file() and dest.stat().st_size > 10_000:
        return dest
    beauty = OUT / "cam_a" / "beauty_01.png"
    if not beauty.is_file():
        beauty = OUT / "beauty_01.png"
    return stylize_img2img(beauty, dest)


def _score_locked() -> dict[str, object]:
    cameras: dict[str, object] = {}
    for cam in CAMERAS:
        cam_dir = OUT / f"cam_{cam}"
        slots = {
            "b3": cam_dir / "panel_01.png",
            "b2": cam_dir / "panel_01_b2.png",
            "beauty": cam_dir / "beauty_01.png",
        }
        if cam == "a":
            slots["b1"] = cam_dir / "panel_01_b1.png"
        rows = {}
        for name, path in slots.items():
            if name == "beauty" or not path.is_file():
                continue
            rows[name] = evaluate_panel(cam_dir, path)
        cameras[f"cam_{cam}"] = rows
    ssims = [
        rows["b3"]["structure"]["ssim_depth"]
        for rows in cameras.values()
        if "b3" in rows
    ]
    mean_ssim = round(sum(ssims) / len(ssims), 4) if ssims else None
    floor_ok = bool(mean_ssim is not None and mean_ssim >= 0.53)
    return {
        "cameras": cameras,
        "mean_ssim_b3": mean_ssim,
        "b3_pass_structure_floor": floor_ok,
        "note": "Hard gate is mean SSIM(depth) >= 0.53 (B2 calibrated). cam_b is often just under per-camera.",
    }


def _bon(judge: bool) -> dict[str, object]:
    db = UsageDB()
    result: dict[str, object] = {}
    for cam in CAMERAS:
        cam_dir = OUT / f"cam_{cam}"
        bon_dir = cam_dir / "bon"
        bon_dir.mkdir(parents=True, exist_ok=True)
        panels: list[Path] = []
        for seed in BON_SEEDS:
            dest = bon_dir / f"seed_{seed}.png"
            if seed == 42:
                src = cam_dir / "panel_01.png"
                if not dest.is_file():
                    shutil.copyfile(src, dest)
            elif not dest.is_file():
                stylize_controlnet(
                    cam_dir / "beauty_01.png",
                    cam_dir / "depth_01.png",
                    cam_dir / "lineart_01.png",
                    dest,
                    seed=seed,
                    style_lora=True,
                )
            panels.append(dest)
        ranked = rank_candidates(cam_dir, panels, db=db, judge=judge)
        winner = Path(str(ranked["winner"]))
        alias = bon_dir / "winner.png"
        shutil.copyfile(winner, alias)
        ranked["winner_alias"] = str(alias)
        result[f"cam_{cam}"] = ranked
    return result


def _judge_catalog() -> list[dict[str, object]]:
    db = UsageDB()
    already = latest_by_pair("gemini")
    rows: list[dict[str, object]] = []
    for spec in PAIRS:
        if spec["id"] in already:
            rows.append({**spec, "skipped": True, "reason": "gemini row exists", "winner": already[spec["id"]].get("winner")})
            continue
        left = resolve_slot(spec["camera"], spec["left"])
        right = resolve_slot(spec["camera"], spec["right"])
        if left is None or right is None:
            rows.append({**spec, "skipped": True, "reason": "missing png"})
            continue
        result = pairwise(left, right, db=db)
        append_pref(
            pair_id=spec["id"],
            camera=spec["camera"],
            left=spec["left"],
            right=spec["right"],
            winner=str(result["winner"]),
            source="gemini",
            axes=dict(result.get("axes") or {}),
            reason=str(result.get("reason") or ""),
        )
        rows.append({**spec, "skipped": False, **result})
    return rows


def _write_scorecard(payload: dict[str, object]) -> Path:
    SCORECARD.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, object] = {}
    if SCORECARD.is_file():
        try:
            existing = json.loads(SCORECARD.read_text())
        except json.JSONDecodeError:
            existing = {}
    merged = dict(existing)
    for key, val in payload.items():
        if val is not None:
            merged[key] = val
    SCORECARD.write_text(json.dumps(merged, indent=2) + "\n")
    return SCORECARD


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="b1 + score + bon + judge")
    parser.add_argument("--b1", action="store_true", help="Restore camera-A B1 img2img PNG")
    parser.add_argument("--score", action="store_true", help="Score existing B2/B3 (and B1 if present)")
    parser.add_argument("--bon", action="store_true", help="Best-of-N seeds 42–45")
    parser.add_argument("--judge", action="store_true", help="Gemini pairwise on the 12 catalog pairs")
    parser.add_argument("--no-bon-judge", action="store_true", help="BoN hard-gate only, skip Gemini knockout")
    parser.add_argument("--agreement", action="store_true", help="Print LLM vs human agreement")
    args = parser.parse_args()
    if args.all:
        args.b1 = args.score = args.bon = args.judge = True
    if not any([args.b1, args.score, args.bon, args.judge, args.agreement]):
        args.score = True

    out: dict[str, object] = {
        "root": str(OUT),
        "scorecard": str(SCORECARD),
        "preferences": str(PREFS_PATH),
        "catalog": pair_catalog(),
    }
    if args.b1:
        out["b1"] = str(_restore_b1())
    if args.score:
        out["locked"] = _score_locked()
    if args.bon:
        out["bon"] = _bon(judge=not args.no_bon_judge)
    if args.judge:
        out["gemini_pairs"] = _judge_catalog()
    if args.agreement or args.judge:
        out["agreement"] = agreement()
    if args.score or args.bon or args.judge or args.agreement:
        card = {
            "locked": out.get("locked"),
            "bon": out.get("bon"),
            "gemini_pairs": out.get("gemini_pairs"),
            "agreement": out.get("agreement"),
            "b1": out.get("b1"),
        }
        _write_scorecard(card)
        out["scorecard"] = str(SCORECARD)
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
