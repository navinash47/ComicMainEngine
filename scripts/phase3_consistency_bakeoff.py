#!/usr/bin/env python3
"""Phase 3 — character consistency bake-off (~15–20 images).

1. Reference sheets (fal FLUX schnell) for key cast
2. Consistency scenes with three methods (subset for cost control):
   - text_only_fal: fal-ai/flux/schnell (text-only baseline)
   - gemini_ref: Gemini Flash Image + reference sheet
   - flux_kontext: fal-ai/flux-pro/kontext + uploaded reference

Images: direct .env (fal/Google). OmniRoute: LLM judge text only.
Writes outputs/phase3/consistency_manifest.json + decision.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.analytics import check_image_quality
from comicengine.characters_phase3 import (
    CHARACTER_LOOKUP,
    PRIORITY_IDS,
    REF_SHEET_IDS,
)
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
from comicengine.style import active_style, build_prompt
from comicengine.tasks import observer
from comicengine.usage import ApiCall, TimedCall, UsageDB

OUT = OUTPUTS / "phase3"
REFS_DIR = OUT / "refs"
SCENES_DIR = OUT / "scenes"
MANIFEST_PATH = OUT / "consistency_manifest.json"
DECISION_PATH = OUT / "decision.json"

# Priority deep bake-off (~10 scenes after ~8 refs = ~18 images)
CONSISTENCY_JOBS = [
    {
        "char_id": "abhijeet_dipke",
        "scene_id": "abhijeet_speak",
        "scene": (
            "Abhijeet Dipke speaks calmly to students with fair-exam placards "
            "near stylized Jantar Mantar at soft dusk; hopeful civic moment"
        ),
        "methods": ["text_only_fal", "gemini_ref", "flux_kontext"],
    },
    {
        "char_id": "abhijeet_dipke",
        "scene_id": "abhijeet_closeup",
        "scene": (
            "medium close-up of Abhijeet Dipke listening carefully, soft outdoor light, "
            "same outfit energy as reference, determined kind expression"
        ),
        "methods": ["text_only_fal", "gemini_ref", "flux_kontext"],
    },
    {
        "char_id": "dad",
        "scene_id": "dad_bedtime",
        "scene": (
            "Dad sits on edge of bed telling a bedtime story, warm lamp light, "
            "gentle smile, cozy Indian home interior"
        ),
        "methods": ["text_only_fal", "gemini_ref"],
    },
    {
        "char_id": "dad",
        "scene_id": "dad_doorway",
        "scene": (
            "Dad in doorway of child's room, soft night light, kind parting look, "
            "same cream sweater / father look as reference"
        ),
        "methods": ["text_only_fal", "gemini_ref"],
    },
    {
        "char_id": "modiji",
        "scene_id": "modi_listen",
        "scene": (
            "Prime Minister Modi listens respectfully in a quiet dignified Delhi hall, "
            "composed posture, no caricature, institutional respect"
        ),
        "methods": ["text_only_fal", "gemini_ref"],
    },
    {
        "char_id": "modiji",
        "scene_id": "modi_window",
        "scene": (
            "Prime Minister Modi by a tall window in soft daylight, thoughtful expression, "
            "saffron or formal kurta-jacket matching reference identity"
        ),
        "methods": ["text_only_fal", "gemini_ref"],
    },
]


def _char_look(char_id: str) -> str:
    c = CHARACTER_LOOKUP[char_id]
    return f"{c.display_name} ({c.look})"


def _ref_prompt(char_id: str) -> str:
    c = CHARACTER_LOOKUP[char_id]
    scene = (
        f"character reference sheet for {c.display_name}: clean front three-quarter portrait, "
        f"neutral soft studio backdrop, clear face and outfit details for identity lock, "
        f"single character only, comic production bible plate"
    )
    return build_prompt(scene, characters=_char_look(char_id))


def _scene_prompt(char_id: str, scene: str) -> str:
    return build_prompt(scene, characters=_char_look(char_id))


def generate_refs(clients: TrackedClients, *, skip_existing: bool) -> list[dict]:
    rows: list[dict] = []
    for cid in REF_SHEET_IDS:
        out = REFS_DIR / f"{cid}_ref.png"
        row: dict = {
            "kind": "ref_sheet",
            "char_id": cid,
            "method": "text_only_fal",
            "path": str(out),
            "status": "pending",
        }
        if skip_existing and out.is_file() and out.stat().st_size > 1000:
            qa = check_image_quality(out)
            row.update({"status": "skipped_existing", "qa": qa})
            rows.append(row)
            print(f"  skip ref {cid} (exists)")
            continue
        try:
            clients.fal_flux_image(
                _ref_prompt(cid),
                out_path=out,
                purpose="char_ref",
                image_size="square_hd",
            )
            qa = check_image_quality(out)
            row.update({"status": "ok", "qa": qa})
            print(f"  ok ref {cid} → {out.name} qa={qa.get('verdict')}")
        except Exception as e:
            row.update({"status": "error", "error": str(e), "trace": traceback.format_exc()[-800:]})
            print(f"  FAIL ref {cid}: {e}")
        rows.append(row)
    return rows


def generate_scenes(clients: TrackedClients, *, skip_existing: bool) -> list[dict]:
    rows: list[dict] = []
    for job in CONSISTENCY_JOBS:
        cid = job["char_id"]
        ref = REFS_DIR / f"{cid}_ref.png"
        prompt = _scene_prompt(cid, job["scene"])
        for method in job["methods"]:
            out = SCENES_DIR / f"{job['scene_id']}__{method}.png"
            row: dict = {
                "kind": "consistency_scene",
                "char_id": cid,
                "scene_id": job["scene_id"],
                "method": method,
                "path": str(out),
                "ref_path": str(ref),
                "status": "pending",
            }
            if not ref.is_file():
                row.update({"status": "error", "error": f"missing ref: {ref}"})
                rows.append(row)
                print(f"  FAIL {out.name}: missing ref")
                continue
            if skip_existing and out.is_file() and out.stat().st_size > 1000:
                qa = check_image_quality(out)
                row.update({"status": "skipped_existing", "qa": qa})
                rows.append(row)
                print(f"  skip {out.name}")
                continue
            try:
                if method == "text_only_fal":
                    clients.fal_flux_image(
                        prompt,
                        out_path=out,
                        purpose="char_consistency",
                        image_size="landscape_4_3",
                    )
                elif method == "gemini_ref":
                    clients.gemini_image_with_refs(
                        prompt,
                        out_path=out,
                        reference_paths=[ref],
                        purpose="char_consistency",
                    )
                elif method == "flux_kontext":
                    clients.fal_kontext_edit(
                        prompt,
                        reference_path=ref,
                        out_path=out,
                        purpose="char_consistency",
                    )
                else:
                    raise ValueError(f"unknown method {method}")
                qa = check_image_quality(out)
                row.update({"status": "ok", "qa": qa})
                print(f"  ok {out.name} qa={qa.get('verdict')}")
            except Exception as e:
                row.update(
                    {"status": "error", "error": str(e), "trace": traceback.format_exc()[-800:]}
                )
                print(f"  FAIL {out.name}: {e}")
            rows.append(row)
    return rows


def local_method_scores(scene_rows: list[dict]) -> dict[str, dict]:
    """Aggregate local QA by method (no vision — file integrity / basic QA)."""
    by: dict[str, list] = {}
    for r in scene_rows:
        if r.get("status") not in ("ok", "skipped_existing"):
            continue
        by.setdefault(r["method"], []).append(r)
    scores: dict[str, dict] = {}
    for method, items in by.items():
        qa_scores = [float((i.get("qa") or {}).get("score") or 0) for i in items]
        passes = sum(1 for i in items if (i.get("qa") or {}).get("verdict") == "pass")
        scores[method] = {
            "n": len(items),
            "avg_qa_score": round(sum(qa_scores) / len(qa_scores), 3) if qa_scores else 0,
            "pass_rate": round(passes / len(items), 3) if items else 0,
            "chars": sorted({i["char_id"] for i in items}),
            "scenes": sorted({i["scene_id"] for i in items}),
        }
    return scores


def judge_consistency(scene_rows: list[dict], local: dict, db: UsageDB) -> dict:
    """Cheap OmniRoute LLM judge on metadata (face/outfit/style consistency proxy)."""
    import anthropic

    model = env("OMNIROUTE_SCRIPT_MODEL") or ("auto/cheap" if USE_OMNIROUTE else "claude-haiku-4-5")
    if USE_OMNIROUTE:
        key = omniroute_api_key()
        if not key:
            raise RuntimeError("OMNIROUTE_API_KEY required for phase3 judge")
        client = anthropic.Anthropic(api_key=key, base_url=omniroute_anthropic_base())
        provider = "omniroute:anthropic"
    else:
        key = env("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY missing")
        client = anthropic.Anthropic(api_key=key)
        provider = "anthropic"

    brief = []
    for r in scene_rows:
        brief.append(
            {
                "char_id": r.get("char_id"),
                "scene_id": r.get("scene_id"),
                "method": r.get("method"),
                "status": r.get("status"),
                "qa": r.get("qa"),
                "error": r.get("error"),
                "path": r.get("path"),
            }
        )

    style = active_style()
    prompt = f"""You are judging CHARACTER CONSISTENCY methods for a Korean manhwa-style bedtime civic comic.

Active style_id: {style.id}
Methods:
- text_only_fal: FLUX schnell text-only (no reference image)
- gemini_ref: Gemini Flash Image conditioned on character reference sheet
- flux_kontext: fal FLUX Kontext with reference image_url

Score each METHOD 1-10 for (reason from generation design + QA/status rates — you cannot see pixels):
- face_identity_lock (likelihood of keeping same face across scenes)
- outfit_stability
- style_match_to_manhwa_lock
- reliability (fewer errors / better local QA)
- cost_efficiency (text_only_fal cheapest; kontext ~$$; gemini mid)

Prioritize Abhijeet Dipke deep bake-off; Dad and Modi used fewer methods.

Return ONLY JSON:
{{
  "rankings": [{{"method": "...", "total": 0, "face_identity_lock": 0, "outfit_stability": 0, "style_match_to_manhwa_lock": 0, "reliability": 0, "cost_efficiency": 0, "why": "short"}}],
  "winner_method": "...",
  "production_recommendation": "1-2 sentences",
  "notes": "caveats"
}}

Local QA aggregates:
{json.dumps(local, indent=2)}

Per-image rows:
{json.dumps(brief, indent=2)}
"""

    call = ApiCall(
        provider=provider,
        model=model,
        purpose="char_consistency_judge",
        phase="phase3",
        meta={"category": "text", "route": routing_label()},
    )
    with TimedCall(db, call):
        msg = client.messages.create(
            model=model,
            max_tokens=1400,
            messages=[{"role": "user", "content": prompt}],
        )
        call.input_tokens = int(msg.usage.input_tokens)
        call.output_tokens = int(msg.usage.output_tokens)
        call.cost_usd = llm_cost_usd(model, call.input_tokens, call.output_tokens)
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")

    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise RuntimeError(f"judge returned no JSON: {text[:300]}")
    return json.loads(text[start : end + 1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-existing", action="store_true", help="Reuse existing PNGs")
    ap.add_argument("--refs-only", action="store_true")
    ap.add_argument("--scenes-only", action="store_true")
    ap.add_argument("--no-judge", action="store_true")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    REFS_DIR.mkdir(parents=True, exist_ok=True)
    SCENES_DIR.mkdir(parents=True, exist_ok=True)

    style = active_style()
    db = UsageDB()
    clients = TrackedClients(db=db, phase="phase3")

    expected_imgs = len(REF_SHEET_IDS) + sum(len(j["methods"]) for j in CONSISTENCY_JOBS)
    print(f"Phase 3 consistency bake-off | style={style.id} | target≈{expected_imgs} images")
    print(f"Routing: images=direct .env | LLM judge={routing_label()}")

    observer.start("phase3", note="character consistency bake-off")
    observer.set_progress("phase3", 0.05, note="generating reference sheets")
    ref_rows: list[dict] = []
    scene_rows: list[dict] = []

    if not args.scenes_only:
        print("\n== Reference sheets ==")
        ref_rows = generate_refs(clients, skip_existing=args.skip_existing)
        observer.set_progress("phase3", 0.4, note=f"refs done ({len(ref_rows)})")

    if not args.refs_only:
        print("\n== Consistency scenes ==")
        scene_rows = generate_scenes(clients, skip_existing=args.skip_existing)
        observer.set_progress("phase3", 0.8, note=f"scenes done ({len(scene_rows)})")

    local = local_method_scores(scene_rows)
    judge: dict = {}
    if not args.no_judge and scene_rows:
        print("\n== OmniRoute LLM judge ==")
        try:
            judge = judge_consistency(scene_rows, local, db)
            print(f"  winner_method={judge.get('winner_method')}")
        except Exception as e:
            judge = {"error": str(e), "winner_method": None}
            print(f"  judge FAIL: {e}")

    ok_imgs = sum(
        1
        for r in ref_rows + scene_rows
        if r.get("status") in ("ok", "skipped_existing")
    )
    fail_imgs = sum(1 for r in ref_rows + scene_rows if r.get("status") == "error")

    # Heuristic fallback if judge missing
    winner = judge.get("winner_method")
    if not winner and local:
        order = ["flux_kontext", "gemini_ref", "text_only_fal"]
        ranked = sorted(
            local.items(),
            key=lambda kv: (
                kv[1]["pass_rate"],
                kv[1]["avg_qa_score"],
                -order.index(kv[0]) if kv[0] in order else 0,
            ),
            reverse=True,
        )
        winner = ranked[0][0] if ranked else None

    decision = {
        "winner_method": winner,
        "production_recommendation": judge.get("production_recommendation")
        or (
            f"Prefer {winner} for identity-critical panels; use text_only_fal for cheap thumbnails."
            if winner
            else "Insufficient successful generations to decide."
        ),
        "local_method_scores": local,
        "judge": judge,
        "style_id": style.id,
        "priority_chars": PRIORITY_IDS,
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }

    manifest = {
        "phase": "phase3",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "style_id": style.id,
        "expected_images": expected_imgs,
        "ok_or_skipped": ok_imgs,
        "failures": fail_imgs,
        "ref_sheet_ids": REF_SHEET_IDS,
        "priority_ids": PRIORITY_IDS,
        "jobs": CONSISTENCY_JOBS,
        "refs": ref_rows,
        "scenes": scene_rows,
        "decision": decision,
        "analytics_note": (
            "All image gens logged with category=image, phase=phase3, purposes "
            "char_ref / char_consistency. LLM judge category=text via OmniRoute."
        ),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    DECISION_PATH.write_text(json.dumps(decision, indent=2), encoding="utf-8")
    observer.set_progress(
        "phase3", 0.95, note=f"manifest written winner={winner} ok={ok_imgs} fail={fail_imgs}"
    )
    if fail_imgs == 0 and winner:
        observer.complete("phase3", note=f"winner={winner}")
    else:
        observer.fail("phase3", error=f"winner={winner} fails={fail_imgs}")

    print(f"\nWrote {MANIFEST_PATH}")
    print(f"Wrote {DECISION_PATH}")
    print(f"Images ok/skip={ok_imgs} fail={fail_imgs} winner={winner}")
    return 0 if fail_imgs == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
