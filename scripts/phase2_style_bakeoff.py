#!/usr/bin/env python3
"""Phase 2 bake-off: compare styles for immersive CJP storytelling vs cost.

Default: fal FLUX.1 schnell (cheap) across styles; optional Gemini samples.
Uses OmniRoute LLM (coding path) to score storytelling fit from metadata + QA.
Writes data/style_lock.json with winner + cheaper runner-up.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.analytics import check_image_quality
from comicengine.characters_cjp import CHARACTER_LOOKUP
from comicengine.clients import TrackedClients
from comicengine.config import (
    OUTPUTS,
    USE_OMNIROUTE,
    env,
    omniroute_anthropic_base,
    omniroute_api_key,
    routing_label,
)
from comicengine.pricing import llm_cost_usd
from comicengine.styles import PRESETS, build_prompt_for, save_lock
from comicengine.tasks import observer
from comicengine.usage import ApiCall, TimedCall, UsageDB

SCENES = [
    {
        "id": "abhijeet_students",
        "ids": ["abhijeet_dipke", "students"],
        "scene": (
            "Abhijeet Dipke speaks gently to students with fair-exam placards near "
            "stylized Jantar Mantar at dusk; emotional but calm civic hope"
        ),
        "story_beat": "youth organizer inspiring peaceful student courage",
    },
    {
        "id": "bedtime_frame",
        "ids": ["dad", "daughter"],
        "scene": (
            "Dad tells Daughter a bedtime story about fair exams; cozy lamp light, "
            "she listens with big curious eyes"
        ),
        "story_beat": "intimate bedtime framing for immersive storytelling",
    },
    {
        "id": "leaders_listen",
        "ids": ["modiji", "amit_shah"],
        "scene": (
            "Prime Minister Modi and Amit Shah listen respectfully in a quiet Delhi hall "
            "as news of student concerns arrives; dignified, not caricature"
        ),
        "story_beat": "institutions hearing citizens with dignity",
    },
]


def _looks(ids: list[str]) -> str:
    return "; ".join(
        f"{CHARACTER_LOOKUP[i].display_name} ({CHARACTER_LOOKUP[i].look})"
        for i in ids
        if i in CHARACTER_LOOKUP
    )


def _judge_with_llm(candidates: list[dict], db: UsageDB) -> dict:
    """Score styles for immersive bedtime civic storytelling + cost/quality tradeoff."""
    import anthropic

    model = env("OMNIROUTE_SCRIPT_MODEL") or ("auto/cheap" if USE_OMNIROUTE else "claude-haiku-4-5")
    if USE_OMNIROUTE:
        key = omniroute_api_key()
        if not key:
            raise RuntimeError("OMNIROUTE_API_KEY required for bake-off judge")
        client = anthropic.Anthropic(api_key=key, base_url=omniroute_anthropic_base())
        provider = "omniroute:anthropic"
    else:
        key = env("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY missing")
        client = anthropic.Anthropic(api_key=key)
        provider = "anthropic"

    brief = []
    for c in candidates:
        brief.append(
            {
                "style_id": c["style_id"],
                "backend": c["backend"],
                "avg_cost_usd": c["avg_cost_usd"],
                "avg_qa": c["avg_qa"],
                "pass_rate": c["pass_rate"],
                "samples": c["samples"],
                "vibe": c["vibe"],
                "scenes": c["scene_ids"],
            }
        )

    prompt = f"""You are art-directing an all-ages bedtime comic about Indian students seeking fair exams
(characters include Dad, Daughter, Abhijeet Dipke, students, PM Modi, Amit Shah — respectful portrayals).

Score each STYLE candidate 1-10 for:
- immersive_storytelling (emotional clarity, scene readability, webtoon/comic immersion)
- bedtime_safety (gentle, age-appropriate, non-caricature leaders)
- civic_dignity (students & leaders shown with respect)
- cost_efficiency (higher if cheaper with acceptable QA)

Return ONLY JSON:
{{
  "rankings": [{{"style_id": "...", "total": 0, "immersive_storytelling": 0, "bedtime_safety": 0, "civic_dignity": 0, "cost_efficiency": 0, "why": "short"}}],
  "winner_style_id": "...",
  "cheaper_good_enough_style_id": "...",
  "recommendation": "1-2 sentences: best lock + when to use cheaper option"
}}

Candidates:
{json.dumps(brief, indent=2)}
"""

    call = ApiCall(
        provider=provider,
        model=model,
        purpose="style_bakeoff_judge",
        phase="phase2",
        meta={"category": "text", "route": routing_label()},
    )
    with TimedCall(db, call):
        msg = client.messages.create(
            model=model,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        call.input_tokens = int(msg.usage.input_tokens)
        call.output_tokens = int(msg.usage.output_tokens)
        call.cost_usd = llm_cost_usd(model, call.input_tokens, call.output_tokens)
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")

    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise RuntimeError(f"judge returned no JSON: {text[:200]}")
    return json.loads(text[start : end + 1])


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--styles",
        default="korean_manhwa,painterly_storybook,graphic_novel,watercolor_editorial",
        help="Comma list of style preset ids",
    )
    p.add_argument("--scenes", type=int, default=2, help="Scenes per style (1-3)")
    p.add_argument("--backend", choices=("fal", "gemini"), default="fal", help="Image backend (fal cheaper)")
    p.add_argument("--fal-model", default="fal-ai/flux/schnell")
    p.add_argument("--gemini-model", default="gemini-3.1-flash-image-preview")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--skip-judge", action="store_true")
    args = p.parse_args()

    style_ids = [s.strip() for s in args.styles.split(",") if s.strip() in PRESETS]
    if not style_ids:
        raise SystemExit(f"No valid styles. Choose from {list(PRESETS)}")
    n_scenes = max(1, min(args.scenes, len(SCENES)))
    scenes = SCENES[:n_scenes]

    out_dir = OUTPUTS / "phase2" / "bakeoff"
    out_dir.mkdir(parents=True, exist_ok=True)
    clients = TrackedClients(phase="phase2")
    db = clients.db
    rows: list[dict] = []

    total = len(style_ids) * n_scenes
    done = 0
    observer.start("phase2", note=f"style bake-off {style_ids} via {args.backend}")

    try:
        for style_id in style_ids:
            style = PRESETS[style_id]
            for i, scene in enumerate(scenes, start=1):
                prompt = build_prompt_for(
                    style,
                    scene["scene"],
                    characters=_looks(scene["ids"]),
                    negative=True,
                )
                fname = f"{style_id}__{scene['id']}__{args.backend}.png"
                path = out_dir / fname
                if args.backend == "fal":
                    clients.fal_flux_image(
                        prompt,
                        out_path=path,
                        model=args.fal_model,
                        purpose="style_bakeoff",
                        seed=args.seed + done,
                    )
                    model = args.fal_model
                else:
                    clients.gemini_image(
                        prompt,
                        out_path=path,
                        model=args.gemini_model,
                        purpose="style_bakeoff",
                    )
                    model = args.gemini_model

                qa = check_image_quality(path)
                # pull last cost from analytics recent matching path is hard; estimate later from DB
                rows.append(
                    {
                        "style_id": style_id,
                        "style_label": style.label,
                        "vibe": style.vibe,
                        "scene_id": scene["id"],
                        "story_beat": scene["story_beat"],
                        "backend": args.backend,
                        "model": model,
                        "path": str(path.relative_to(ROOT)),
                        "qa": qa,
                        "prompt": prompt,
                    }
                )
                done += 1
                observer.set_progress("phase2", done / (total + 1), note=f"{style_id}/{scene['id']}")
                print(f"[{done}/{total}] {style_id} · {scene['id']} · qa={qa.get('verdict')}")

        # Attach approx costs from recent fal/gemini phase2 image calls
        from comicengine.analytics import analytics

        recent = analytics.calls(limit=200, category="image", phase="phase2")
        cost_by_path = {}
        for c in recent:
            meta = c.get("meta") or {}
            op = meta.get("out_path") or ""
            if op:
                cost_by_path[op] = float(c.get("cost_usd") or 0)

        for r in rows:
            abs_path = str((ROOT / r["path"]).resolve())
            # clients store path as given
            r["cost_usd"] = cost_by_path.get(abs_path) or cost_by_path.get(str(ROOT / r["path"])) or (
                0.003 if args.backend == "fal" else 0.039
            )

        # Aggregate per style
        by_style: dict[str, list[dict]] = {}
        for r in rows:
            by_style.setdefault(r["style_id"], []).append(r)

        candidates = []
        for sid, items in by_style.items():
            costs = [float(x["cost_usd"]) for x in items]
            scores = [float((x.get("qa") or {}).get("score") or 0) for x in items]
            candidates.append(
                {
                    "style_id": sid,
                    "label": PRESETS[sid].label,
                    "vibe": PRESETS[sid].vibe,
                    "backend": args.backend,
                    "samples": len(items),
                    "avg_cost_usd": round(sum(costs) / len(costs), 6),
                    "total_cost_usd": round(sum(costs), 6),
                    "avg_qa": round(sum(scores) / len(scores), 3),
                    "pass_rate": round(sum(1 for s in scores if s >= 0.8) / len(scores), 3),
                    "scene_ids": [x["scene_id"] for x in items],
                    "images": [x["path"] for x in items],
                }
            )

        judge = None
        if not args.skip_judge:
            judge = _judge_with_llm(candidates, db)

        # Determine winners
        if judge and judge.get("winner_style_id") in PRESETS:
            winner = judge["winner_style_id"]
            cheaper = judge.get("cheaper_good_enough_style_id") or winner
        else:
            # fallback: best QA, then lowest cost
            winner = sorted(candidates, key=lambda c: (-c["avg_qa"], c["avg_cost_usd"]))[0]["style_id"]
            cheaper = sorted(candidates, key=lambda c: (c["avg_cost_usd"], -c["avg_qa"]))[0]["style_id"]

        # Copy primary anchor from winner's best QA image
        winner_rows = by_style[winner]
        best_img = max(winner_rows, key=lambda r: float((r.get("qa") or {}).get("score") or 0))
        anchor = OUTPUTS / "phase2" / "style_anchor.png"
        anchor.write_bytes((ROOT / best_img["path"]).read_bytes())

        lock = {
            "winner_style_id": winner,
            "cheaper_good_enough_style_id": cheaper,
            "backend_image": args.backend,
            "fal_model": args.fal_model if args.backend == "fal" else None,
            "gemini_model": args.gemini_model if args.backend == "gemini" else None,
            "anchor_path": str(anchor.relative_to(ROOT)),
            "candidates": candidates,
            "judge": judge,
            "recommendation": (judge or {}).get("recommendation")
            or f"Lock {winner}; use {cheaper} when optimizing cost.",
            "note": "Active style via comicengine.style.active_style()/build_prompt().",
        }
        lock_path = save_lock(lock)

        manifest = {
            "phase": "phase2_bakeoff",
            "rows": rows,
            "lock": lock,
        }
        man = out_dir / "bakeoff_manifest.json"
        man.write_text(json.dumps(manifest, indent=2))

        observer.complete(
            "phase2",
            note=f"winner={winner}; cheaper={cheaper}; n={len(rows)}",
        )
        print(json.dumps({"winner": winner, "cheaper": cheaper, "lock": str(lock_path)}, indent=2))
        print(f"anchor -> {anchor}")
        print("Images: http://127.0.0.1:8765/images")
        print("Analytics: http://127.0.0.1:8765/analytics")
    except Exception as e:  # noqa: BLE001
        observer.fail("phase2", str(e))
        raise
    finally:
        observer.refresh_from_world()


if __name__ == "__main__":
    main()
