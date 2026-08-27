"""Append-only preference log + the 12 G1 A/B pairs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from comicengine.config import OUTPUTS, ROOT

PREFS_PATH = ROOT / "data" / "v2b" / "eval" / "preferences.jsonl"
ROOT_DIR = OUTPUTS / "v2b" / "himym_ep01"

# Human catalog. B1 only on camera A. BoN winners filled after --bon.
PAIRS: list[dict[str, str]] = [
    {"id": "a_b1_b2", "camera": "a", "left": "b1", "right": "b2"},
    {"id": "a_b2_b3", "camera": "a", "left": "b2", "right": "b3"},
    {"id": "a_b1_b3", "camera": "a", "left": "b1", "right": "b3"},
    {"id": "a_b3_beauty", "camera": "a", "left": "b3", "right": "beauty"},
    {"id": "b_b2_b3", "camera": "b", "left": "b2", "right": "b3"},
    {"id": "b_b2_beauty", "camera": "b", "left": "b2", "right": "beauty"},
    {"id": "b_b3_beauty", "camera": "b", "left": "b3", "right": "beauty"},
    {"id": "b_bon_b3", "camera": "b", "left": "bon_winner", "right": "b3"},
    {"id": "c_b2_b3", "camera": "c", "left": "b2", "right": "b3"},
    {"id": "c_b2_beauty", "camera": "c", "left": "b2", "right": "beauty"},
    {"id": "c_b3_beauty", "camera": "c", "left": "b3", "right": "beauty"},
    {"id": "c_bon_b3", "camera": "c", "left": "bon_winner", "right": "b3"},
]


def _cam(camera: str) -> Path:
    return ROOT_DIR / f"cam_{camera}"


def resolve_slot(camera: str, slot: str) -> Path | None:
    cam = _cam(camera)
    mapping = {
        "beauty": cam / "beauty_01.png",
        "b1": cam / "panel_01_b1.png",
        "b2": cam / "panel_01_b2.png",
        "b3": cam / "panel_01.png",
        "bon_winner": cam / "bon" / "winner.png",
    }
    path = mapping.get(slot)
    if path is None or not path.is_file():
        return None
    return path


def media_url(path: Path) -> str:
    rel = path.resolve().relative_to(OUTPUTS.resolve())
    return "/media/" + str(rel).replace("\\", "/")


def pair_catalog() -> list[dict[str, Any]]:
    labeled = {row["pair_id"]: row for row in load_prefs() if row.get("source") == "human"}
    out: list[dict[str, Any]] = []
    for spec in PAIRS:
        left = resolve_slot(spec["camera"], spec["left"])
        right = resolve_slot(spec["camera"], spec["right"])
        ready = left is not None and right is not None
        human = labeled.get(spec["id"])
        out.append(
            {
                **spec,
                "ready": ready,
                "left_url": media_url(left) if left else None,
                "right_url": media_url(right) if right else None,
                "human_winner": (human or {}).get("winner"),
            }
        )
    return out


def append_pref(
    *,
    pair_id: str,
    camera: str,
    left: str,
    right: str,
    winner: str,
    source: str,
    axes: dict[str, Any] | None = None,
    reason: str = "",
) -> dict[str, Any]:
    if winner not in {"A", "B", "tie"}:
        raise ValueError("winner must be A, B, or tie")
    row = {
        "pair_id": pair_id,
        "camera": camera,
        "left": left,
        "right": right,
        "winner": winner,
        "source": source,
        "axes": axes or {},
        "reason": reason,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PREFS_PATH.open("a") as fh:
        fh.write(json.dumps(row) + "\n")
    return row


def load_prefs() -> list[dict[str, Any]]:
    if not PREFS_PATH.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in PREFS_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def latest_by_pair(source: str) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in load_prefs():
        if row.get("source") == source and row.get("pair_id"):
            latest[str(row["pair_id"])] = row
    return latest


def agreement() -> dict[str, Any]:
    gem = latest_by_pair("gemini")
    hum = latest_by_pair("human")
    shared = sorted(set(gem) & set(hum))
    matches = 0
    lenient = 0
    details = []
    for pid in shared:
        gw, hw = gem[pid]["winner"], hum[pid]["winner"]
        ok = gw == hw or "tie" in {gw, hw}
        if gw == hw:
            matches += 1
        if ok:
            lenient += 1
        details.append({"pair_id": pid, "gemini": gw, "human": hw, "match": gw == hw, "tie_lenient": ok})
    n = len(shared)
    return {
        "n_shared": n,
        "n_human": len(hum),
        "n_gemini": len(gem),
        "exact_matches": matches,
        "exact_rate": round(matches / n, 3) if n else None,
        "tie_lenient_matches": lenient,
        "tie_lenient_rate": round(lenient / n, 3) if n else None,
        "target": "8/12",
        "pass_target": matches >= 8 if n >= 12 else False,
        "details": details,
        "note": "G1 still passes the harness if exact rate is below 8/12; that is calibration debt, not an RL train signal. Ties count as lenient agreement.",
    }
