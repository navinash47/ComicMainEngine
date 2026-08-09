"""Discover episode JSON scripts under outputs/ for the dashboard Stories section."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from comicengine.config import OUTPUTS, ROOT


def _safe_under_outputs(path: Path) -> Path | None:
    try:
        resolved = path.resolve()
        outputs = OUTPUTS.resolve()
        if outputs not in resolved.parents and resolved != outputs:
            return None
        if not resolved.is_file() or resolved.suffix.lower() != ".json":
            return None
        return resolved
    except OSError:
        return None


def list_stories() -> list[dict[str, Any]]:
    stories: list[dict[str, Any]] = []
    if not OUTPUTS.exists():
        return stories
    for path in sorted(OUTPUTS.rglob("*.json")):
        if path.name.startswith("."):
            continue
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict) or "panels" not in data:
            continue
        panels = data.get("panels") or []
        rel = path.relative_to(ROOT).as_posix()
        slug = path.stem
        stories.append(
            {
                "id": slug,
                "title": data.get("title") or slug,
                "topic": data.get("topic") or "",
                "voice": data.get("voice") or "",
                "panel_count": len(panels),
                "season": data.get("season"),
                "episode_no": data.get("episode_no"),
                "phase": path.parent.name,
                "path": rel,
                "href": f"/stories/{slug}",
                "json_href": f"/api/stories/{slug}",
                "disclaimer": (data.get("disclaimer") or "")[:180],
            }
        )
    # Prefer unique stems; if collision, keep first
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for s in stories:
        if s["id"] in seen:
            s["id"] = f"{s['phase']}__{s['id']}"
            s["href"] = f"/stories/{s['id']}"
            s["json_href"] = f"/api/stories/{s['id']}"
        seen.add(s["id"])
        unique.append(s)
    return unique


def _resolve_story_path(story_id: str) -> Path | None:
    # Exact stem match first, then phase__stem
    candidates = list(OUTPUTS.rglob("*.json")) if OUTPUTS.exists() else []
    if "__" in story_id:
        phase, stem = story_id.split("__", 1)
        for p in candidates:
            if p.parent.name == phase and p.stem == stem:
                return p
    for p in candidates:
        if p.stem == story_id:
            return p
    return None


def load_story(story_id: str) -> dict[str, Any] | None:
    path = _resolve_story_path(story_id)
    if not path:
        return None
    safe = _safe_under_outputs(path)
    if not safe:
        return None
    data = json.loads(safe.read_text())
    rel = safe.relative_to(ROOT).as_posix()
    return {
        "id": story_id,
        "path": rel,
        "episode": data,
    }
