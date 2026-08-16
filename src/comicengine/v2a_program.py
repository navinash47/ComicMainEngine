"""Load Version 2A program JSON (parallel track; do not touch v2_program.json)."""

from __future__ import annotations

import json
from typing import Any

from comicengine.config import ROOT

PROGRAM_PATH = ROOT / "data" / "v2a_program.json"
ARCHITECTURE_PATH = ROOT / "docs" / "V2A_ARCHITECTURE.md"


def load_program() -> dict[str, Any]:
    if not PROGRAM_PATH.is_file():
        return {
            "program": {"version": "2A", "active_phase_id": None},
            "phase_ids": [],
            "phases": {},
            "error": f"missing {PROGRAM_PATH}",
        }
    data = json.loads(PROGRAM_PATH.read_text())
    data["source"] = "local"
    data["paths"] = {
        "program": str(PROGRAM_PATH.relative_to(ROOT)),
        "architecture": str(ARCHITECTURE_PATH.relative_to(ROOT)) if ARCHITECTURE_PATH.is_file() else None,
    }
    return data
