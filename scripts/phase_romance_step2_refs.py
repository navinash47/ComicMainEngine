#!/usr/bin/env python3
"""Romance Step 2 — manhwa character reference sheets for HIMYM cast."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

os.environ.setdefault("STYLE_ID", "korean_manhwa")

from comicengine.config import OUTPUTS
from comicengine.episode_schema import Episode
from comicengine.panel_batch import ensure_ref
from comicengine.clients import TrackedClients
from comicengine.tasks import observer

EPISODE = OUTPUTS / "phase4" / "episode_how_i_met_your_mother_ep1.json"


def main() -> None:
    if not EPISODE.is_file():
        raise SystemExit(f"missing script — run step1 first: {EPISODE}")

    observer.upsert(
        "phase_romance_step2",
        title="Romance Step 2 — Manhwa character refs",
        description="Rohan / Elena / Maya / Dad / friends reference sheets",
        phase="phase_romance_step2",
        sort_order=210,
        status="in_progress",
        progress=0.05,
    )
    try:
        ep = Episode.model_validate(json.loads(EPISODE.read_text()))
        clients = TrackedClients(phase="phase_romance_step2")
        rows = []
        chars = list(ep.characters)
        for i, char in enumerate(chars):
            observer.set_progress(
                "phase_romance_step2",
                0.1 + 0.8 * (i / max(len(chars), 1)),
                note=f"ref {char.id}…",
            )
            path = ensure_ref(clients, char, skip_existing=True)
            rows.append(
                {
                    "id": char.id,
                    "path": str(path) if path else None,
                    "ok": bool(path and path.is_file()),
                }
            )
            print(f"ref {char.id}: {'ok' if path else 'FAIL'}")

        out = OUTPUTS / "romance" / "step2_refs_manifest.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"refs": rows}, indent=2))
        ok = sum(1 for r in rows if r["ok"])
        observer.complete(
            "phase_romance_step2",
            note=f"{ok}/{len(rows)} refs · manhwa",
        )
        print(f"done {ok}/{len(rows)} → {out}")
    except Exception as e:  # noqa: BLE001
        observer.fail("phase_romance_step2", str(e))
        raise


if __name__ == "__main__":
    main()
