"""Load Version 2B program JSON (parallel track; do not touch v2 or v2a program JSON)."""

from __future__ import annotations

import json
from typing import Any

from comicengine.config import ROOT

PROGRAM_PATH = ROOT / "data" / "v2b_program.json"
ARCHITECTURE_PATH = ROOT / "docs" / "V2B_ARCHITECTURE.md"
SOURCE_PLAN_PATH = ROOT / "docs" / "V2B_SOURCE_PLAN.md"
EP01_PATH = ROOT / "data" / "v2b" / "episodes" / "ep01.json"


def load_program() -> dict[str, Any]:
    if not PROGRAM_PATH.is_file():
        return {
            "program": {"version": "2B", "active_phase_id": None},
            "phase_ids": [],
            "phases": {},
            "error": f"missing {PROGRAM_PATH}",
        }
    data = json.loads(PROGRAM_PATH.read_text())
    data["source"] = "local"
    data["paths"] = {
        "program": str(PROGRAM_PATH.relative_to(ROOT)),
        "architecture": str(ARCHITECTURE_PATH.relative_to(ROOT)) if ARCHITECTURE_PATH.is_file() else None,
        "source_plan": str(SOURCE_PLAN_PATH.relative_to(ROOT)) if SOURCE_PLAN_PATH.is_file() else None,
        "ep01": str(EP01_PATH.relative_to(ROOT)) if EP01_PATH.is_file() else None,
    }
    if EP01_PATH.is_file():
        ep = json.loads(EP01_PATH.read_text())
        data["ep01"] = {
            "id": ep.get("id"),
            "title": ep.get("title"),
            "panel_count": ep.get("panel_count"),
            "story_goal": ep.get("story_goal"),
            "framework_goal": ep.get("framework_goal"),
            "gate": ep.get("gate"),
            "b1_prove": ep.get("b1_prove"),
            "leads": ep.get("leads"),
            "supporting": ep.get("supporting"),
        }
    return data
