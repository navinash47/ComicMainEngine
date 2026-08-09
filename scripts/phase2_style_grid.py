#!/usr/bin/env python3
"""Phase 2 — style lock grid with CJP cast (Abhijeet, Modiji, students, Dad/Daughter).

Runs BOTH fal FLUX.1 schnell and Gemini image for the same scenes, logs each call
to analytics (category=image), writes style anchors + comparison manifest.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.analytics import check_image_quality
from comicengine.characters_cjp import CHARACTER_LOOKUP, CHARACTERS
from comicengine.clients import TrackedClients
from comicengine.config import OUTPUTS
from comicengine.style import STYLE_SUFFIX, build_prompt
from comicengine.tasks import observer

# Style-lock scenes featuring recurring public/test cast (respectful, bedtime tone)
SCENES = [
    {
        "id": "bedtime_open",
        "ids": ["dad", "daughter"],
        "scene": (
            "Dad and Daughter sitting on a cozy bed under a warm lamp, opening a picture book "
            "about fairness in exams; soft golden room, Korean manhwa webtoon framing"
        ),
    },
    {
        "id": "abhijeet_students",
        "ids": ["abhijeet_dipke", "students"],
        "scene": (
            "Abhijeet Dipke speaking gently to a small circle of students with fair-exam placards "
            "near stylized Jantar Mantar arches at dusk, manhwa crowd composition"
        ),
    },
    {
        "id": "leaders_listen",
        "ids": ["modiji", "amit_shah", "students"],
        "scene": (
            "Far away in a calm Delhi government hall, Prime Minister Modi and Amit Shah listen "
            "thoughtfully as tiny messengers bring news of student concerns; dignified manhwa portraiture, not caricature"
        ),
    },
    {
        "id": "study_night",
        "ids": ["students", "daughter"],
        "scene": (
            "College students studying by lamplight with books while Daughter imagines their story "
            "from her bedroom window; hopeful Korean webtoon mood"
        ),
    },
    {
        "id": "together_hope",
        "ids": ["dad", "daughter", "abhijeet_dipke", "students"],
        "scene": (
            "Dad and Daughter dream of Abhijeet and students planting a seedling labeled Fair Exams "
            "under a kind sunrise; emotional manhwa ending splash panel"
        ),
    },
]


def _looks(ids: list[str]) -> str:
    parts = []
    for i in ids:
        c = CHARACTER_LOOKUP.get(i)
        if c:
            parts.append(f"{c.display_name} ({c.look})")
    return "; ".join(parts)


def _gen_one(
    clients: TrackedClients,
    *,
    backend: str,
    scene: dict,
    index: int,
    out_dir: Path,
    fal_model: str,
    gemini_model: str,
    seed: int | None,
) -> dict:
    char_line = _looks(scene["ids"])
    prompt = build_prompt(scene["scene"], characters=char_line)
    purpose = "style_grid"

    if backend == "fal":
        path = out_dir / f"style_fal_{index:02d}_{scene['id']}.png"
        clients.fal_flux_image(
            prompt,
            out_path=path,
            model=fal_model,
            purpose=purpose,
            seed=seed,
        )
        model = fal_model
    else:
        path = out_dir / f"style_gemini_{index:02d}_{scene['id']}.png"
        clients.gemini_image(
            prompt,
            out_path=path,
            model=gemini_model,
            purpose=purpose,
        )
        model = gemini_model

    qa = check_image_quality(path)
    return {
        "backend": backend,
        "model": model,
        "scene_id": scene["id"],
        "characters": scene["ids"],
        "path": str(path.relative_to(ROOT)),
        "prompt": prompt,
        "style_suffix": STYLE_SUFFIX,
        "image_quality": qa,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=3, help="Scenes per backend (max 5)")
    p.add_argument("--backends", default="fal,gemini", help="Comma list: fal,gemini")
    p.add_argument("--fal-model", default="fal-ai/flux/schnell")
    p.add_argument("--gemini-model", default="gemini-3.1-flash-image-preview")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    n = max(1, min(args.count, len(SCENES)))
    backends = [b.strip() for b in args.backends.split(",") if b.strip() in {"fal", "gemini"}]
    if not backends:
        raise SystemExit("Need at least one backend: fal and/or gemini")

    out_dir = OUTPUTS / "phase2"
    out_dir.mkdir(parents=True, exist_ok=True)
    clients = TrackedClients(phase="phase2")
    results: list[dict] = []

    observer.start("phase2", note=f"style lock {backends} x{n} CJP cast")
    try:
        total = len(backends) * n
        done = 0
        for backend in backends:
            for i, scene in enumerate(SCENES[:n], start=1):
                row = _gen_one(
                    clients,
                    backend=backend,
                    scene=scene,
                    index=i,
                    out_dir=out_dir,
                    fal_model=args.fal_model,
                    gemini_model=args.gemini_model,
                    seed=args.seed + i if backend == "fal" else None,
                )
                results.append(row)
                done += 1
                observer.set_progress("phase2", done / total, note=f"{backend} {scene['id']}")
                print(f"[{done}/{total}] {backend} {scene['id']} qa={row['image_quality'].get('verdict')}")

        # Provisional anchors: best QA per backend
        anchors = {}
        for backend in backends:
            subset = [r for r in results if r["backend"] == backend]
            best = max(subset, key=lambda r: float((r.get("image_quality") or {}).get("score") or 0))
            src = ROOT / best["path"]
            anchor = out_dir / f"style_anchor_{backend}.png"
            if src.exists():
                anchor.write_bytes(src.read_bytes())
                anchors[backend] = {
                    "path": str(anchor.relative_to(ROOT)),
                    "from_scene": best["scene_id"],
                    "qa_score": best["image_quality"].get("score"),
                }

        # Prefer fal anchor as primary style_anchor.png if present
        primary = out_dir / "style_anchor.png"
        if "fal" in anchors:
            primary.write_bytes((ROOT / anchors["fal"]["path"]).read_bytes())
        elif results:
            primary.write_bytes((ROOT / results[0]["path"]).read_bytes())

        # Evaluation summary
        eval_rows = []
        for backend in backends:
            subset = [r for r in results if r["backend"] == backend]
            scores = [float((r.get("image_quality") or {}).get("score") or 0) for r in subset]
            avg = sum(scores) / len(scores) if scores else 0
            pass_rate = sum(1 for s in scores if s >= 0.8) / len(scores) if scores else 0
            eval_rows.append(
                {
                    "backend": backend,
                    "samples": len(subset),
                    "avg_qa": round(avg, 3),
                    "pass_rate": round(pass_rate, 3),
                    "recommendation": (
                        "prefer for drafts/speed" if backend == "fal" else "prefer for prompt reasoning / finals candidate"
                    ),
                }
            )
        # Pick winner by avg QA then pass rate
        winner = sorted(eval_rows, key=lambda e: (-e["avg_qa"], -e["pass_rate"]))[0]["backend"]

        manifest = {
            "phase": "phase2",
            "cast": [c.model_dump() for c in CHARACTERS],
            "style_suffix": STYLE_SUFFIX,
            "backends": backends,
            "results": results,
            "anchors": anchors,
            "primary_anchor": str(primary.relative_to(ROOT)) if primary.exists() else None,
            "evaluation": {"by_backend": eval_rows, "winner_by_qa": winner},
            "note": (
                "Dramatized Korean manhwa likenesses for pipeline testing. "
                "Treat named leaders respectfully; not photoreal portraits."
            ),
        }
        man_path = out_dir / "style_manifest.json"
        man_path.write_text(json.dumps(manifest, indent=2))
        observer.complete("phase2", note=f"winner_by_qa={winner}; {len(results)} images")
        print(f"manifest -> {man_path}")
        print(f"evaluation -> {json.dumps(manifest['evaluation'], indent=2)}")
        print("Images tab: http://127.0.0.1:8765/images")
    except Exception as e:  # noqa: BLE001
        observer.fail("phase2", str(e))
        raise
    finally:
        observer.refresh_from_world()


if __name__ == "__main__":
    main()
