"""Gemini Flash pairwise vision judge. Direct GOOGLE_API_KEY — never OmniRoute."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from comicengine.config import env
from comicengine.pricing import llm_cost_usd
from comicengine.usage import ApiCall, TimedCall, UsageDB

JUDGE_MODEL = env("V2B_G1_JUDGE_MODEL") or "gemini-3.6-flash"
SPEC = (
    "HIMYM Episode 1 panel 1: night living room, Indian father and teenage daughter "
    "sitting on a sofa, warm lamp from upper-left, medium two-shot. Geometry should "
    "keep two seated figures on a sofa (not restage into speech-bubble/cloak). Style "
    "should read as intentional storybook illustration, bedtime-safe dad-to-daughter."
)
PROMPT = f"""You compare two comic-pipeline stills of the SAME shot.

Scene contract: {SPEC}

Image A is the first image. Image B is the second.

Return ONLY JSON:
{{
  "winner": "A" | "B" | "tie",
  "structure": "A" | "B" | "tie",
  "style": "A" | "B" | "tie",
  "lighting": "A" | "B" | "tie",
  "bedtime": "A" | "B" | "tie",
  "reason": "one short sentence"
}}

Rules:
- pairwise only. Do not output 1-10 scores.
- structure: which keeps sofa + two figures and the 3D camera.
- style: which is more intentional storybook/comic, less generic SD slop.
- lighting: which better keeps a warm key light from upper-left.
- bedtime: which is safer/cozier for a dad-to-daughter bedtime comic.
- winner: overall for this pipeline (structure first, then style, then lighting/bedtime).
"""


def _flip_letter(val: str) -> str:
    if val == "A":
        return "B"
    if val == "B":
        return "A"
    return val


def _parse_json(text: str) -> dict[str, Any]:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise RuntimeError(f"judge returned no JSON: {text[:400]}")
    data = json.loads(text[start : end + 1])
    for key in ("winner", "structure", "style", "lighting", "bedtime"):
        val = str(data.get(key) or "tie")
        if val not in {"A", "B", "tie"}:
            val = "tie"
        data[key] = val
    data["reason"] = str(data.get("reason") or "")[:400]
    return data


def _one_pass(path_a: Path, path_b: Path, db: UsageDB, prompt: str | None = None) -> dict[str, Any]:
    from google import genai
    from google.genai import types

    key = env("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GOOGLE_API_KEY missing in .env")
    client = genai.Client(api_key=key)
    mime_a = "image/png"
    mime_b = "image/png"
    call = ApiCall(
        provider="google",
        model=JUDGE_MODEL,
        purpose="v2b_g1_judge",
        phase="g1",
        meta={"route": "direct", "a": str(path_a), "b": str(path_b)},
    )
    with TimedCall(db, call):
        resp = client.models.generate_content(
            model=JUDGE_MODEL,
            contents=[
                prompt or PROMPT,
                types.Part.from_bytes(data=Path(path_a).read_bytes(), mime_type=mime_a),
                types.Part.from_bytes(data=Path(path_b).read_bytes(), mime_type=mime_b),
            ],
        )
        um = getattr(resp, "usage_metadata", None)
        if um:
            call.input_tokens = int(getattr(um, "prompt_token_count", 0) or 0)
            call.output_tokens = int(getattr(um, "candidates_token_count", 0) or 0)
        call.cost_usd = llm_cost_usd(JUDGE_MODEL, call.input_tokens, call.output_tokens)
        text = (getattr(resp, "text", None) or "").strip()
        if not text:
            parts = []
            for cand in getattr(resp, "candidates", None) or []:
                content = getattr(cand, "content", None)
                for part in getattr(content, "parts", None) or []:
                    if getattr(part, "text", None):
                        parts.append(part.text)
            text = "\n".join(parts)
        call.meta["preview"] = text[:120]
        parsed = _parse_json(text)
        call.meta["winner"] = parsed.get("winner")
        return parsed


def _vote(first: str, second_flipped: str) -> str:
    if first == second_flipped:
        return first
    if first == "tie":
        return second_flipped
    if second_flipped == "tie":
        return first
    return "tie"


def pairwise(path_a: Path, path_b: Path, *, db: UsageDB | None = None) -> dict[str, Any]:
    """Run A/B then swapped B/A; average. Winner is relative to original A/B order."""
    db = db or UsageDB()
    forward = _one_pass(path_a, path_b, db)
    backward = _one_pass(path_b, path_a, db)
    flipped = {k: _flip_letter(str(backward.get(k))) for k in ("winner", "structure", "style", "lighting", "bedtime")}
    axes = {k: _vote(str(forward.get(k)), flipped[k]) for k in ("structure", "style", "lighting", "bedtime")}
    winner = _vote(str(forward.get("winner")), flipped["winner"])
    if winner == "tie":
        # third pass only when swap disagrees
        third = _one_pass(path_a, path_b, db)
        winner = str(third.get("winner") or "tie")
        if winner not in {"A", "B", "tie"}:
            winner = "tie"
        for k in axes:
            axes[k] = str(third.get(k) or axes[k])
    return {
        "winner": winner,
        "axes": axes,
        "reason": forward.get("reason") or "",
        "forward": forward,
        "backward_flipped": flipped,
    }


IDENTITY_PROMPT = """Image A is a character reference. Image B is a candidate still.

Question: is B the SAME PERSON as A (identity: hair, face mass, clothes type)? Ignore pose and camera.

Return ONLY JSON:
{
  "winner": "B" | "A" | "tie",
  "structure": "tie",
  "style": "tie",
  "lighting": "tie",
  "bedtime": "tie",
  "reason": "one short sentence"
}

Rules:
- winner B means B is the same person as A.
- winner A means B is a different person.
- tie if unsure.
- pairwise only. Do not output 1-10 scores.
"""


def same_person(reference: Path, candidate: Path, *, db: UsageDB | None = None) -> dict[str, Any]:
    """True when Gemini says the candidate is the same person as the reference."""
    db = db or UsageDB()
    forward = _one_pass(reference, candidate, db, prompt=IDENTITY_PROMPT)
    backward = _one_pass(candidate, reference, db, prompt=IDENTITY_PROMPT)
    # forward winner B = same. backward (swapped) winner A = same in original terms.
    fwd_same = forward.get("winner") == "B"
    back_same = backward.get("winner") == "A"
    if fwd_same and back_same:
        same = True
    elif (not fwd_same) and (not back_same) and forward.get("winner") != "tie" and backward.get("winner") != "tie":
        same = False
    elif forward.get("winner") == "tie" and backward.get("winner") == "tie":
        same = False
    else:
        third = _one_pass(reference, candidate, db, prompt=IDENTITY_PROMPT)
        same = third.get("winner") == "B"
    return {
        "same": same,
        "reason": forward.get("reason") or "",
        "forward": forward,
        "backward": backward,
    }
