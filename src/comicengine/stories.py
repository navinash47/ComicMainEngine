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
        # Only episode scripts — ignore phase manifests / summaries / library catalogs
        if path.name in {"manifest.json", "catalog.json", "batch_summary.json", "assemble_summary.json", "compose_summary.json", "consistency_manifest.json", "decision.json"}:
            continue
        if not path.name.startswith("episode_"):
            continue
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict) or "panels" not in data:
            continue
        if "title" not in data or "characters" not in data:
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

    # Prefer Phase 6 composed art; fall back to Phase 5 raw panels
    panels = data.get("panels") or []
    for panel in panels:
        if not isinstance(panel, dict):
            continue
        composed = panel.get("composed_image_path")
        raw = panel.get("image_path")
        chosen = composed or raw
        if chosen:
            media = str(chosen).replace("\\", "/")
            if media.startswith("outputs/"):
                media = media[len("outputs/") :]
            panel["image_href"] = f"/media/{media}"
            panel["image_kind"] = "composed" if composed else "raw"

    # Attach Phase 8/8.5 curation (rating, suggestions, status) per panel
    from comicengine.curation import curation

    cur_map = {
        i.get("panel_index"): i
        for i in curation.list(story_id=story_id, kind="panel")
    }
    for panel in panels:
        if not isinstance(panel, dict):
            continue
        item = cur_map.get(panel.get("index")) or {}
        panel["curation"] = {
            "status": item.get("status") or "pending",
            "rating": item.get("rating"),
            "suggestions": item.get("suggestions") or "",
            "note": item.get("note") or "",
            "updated_at": item.get("updated_at"),
        }
        if panel.get("image_href") and item.get("updated_at"):
            panel["image_href"] = f"{panel['image_href']}?v={item['updated_at']}"

    bridges: list[dict[str, Any]] = []
    man_path = OUTPUTS / "phase6" / path.stem / "manifest.json"
    if man_path.is_file():
        try:
            man = json.loads(man_path.read_text())
            bridges = list(man.get("bridges") or [])
        except (OSError, json.JSONDecodeError):
            bridges = []
    if not bridges:
        # lightweight interstitial from scene descriptions
        for i, panel in enumerate(panels):
            if not isinstance(panel, dict):
                continue
            text = (panel.get("scene_description") or "").strip()
            if i == 0 and data.get("narrative_summary"):
                text = f"{data.get('narrative_summary')}\n\n{text}".strip()
            bridges.append({"before_panel": panel.get("index"), "text": text})

    assembly: dict[str, Any] = {}
    man7 = OUTPUTS / "phase7" / path.stem / "manifest.json"
    if man7.is_file():
        try:
            assembly = json.loads(man7.read_text())
        except (OSError, json.JSONDecodeError):
            assembly = {}
    if not assembly:
        if data.get("webtoon_path") or data.get("pdf_path"):
            wt = data.get("webtoon_path") or ""
            pdf = data.get("pdf_path") or ""
            assembly = {
                "webtoon_path": wt,
                "pdf_path": pdf,
                "webtoon_href": f"/media/{wt[len('outputs/'):]}" if wt.startswith("outputs/") else "",
                "pdf_href": f"/media/{pdf[len('outputs/'):]}" if pdf.startswith("outputs/") else "",
            }

    assembly_image_only: dict[str, Any] = {}
    man75 = OUTPUTS / "phase7.5" / path.stem / "manifest.json"
    if man75.is_file():
        try:
            assembly_image_only = json.loads(man75.read_text())
        except (OSError, json.JSONDecodeError):
            assembly_image_only = {}
    if not assembly_image_only and (
        data.get("webtoon_image_only_path") or data.get("pdf_image_only_path")
    ):
        wt = data.get("webtoon_image_only_path") or ""
        pdf = data.get("pdf_image_only_path") or ""
        assembly_image_only = {
            "webtoon_path": wt,
            "pdf_path": pdf,
            "webtoon_href": f"/media/{wt[len('outputs/'):]}" if wt.startswith("outputs/") else "",
            "pdf_href": f"/media/{pdf[len('outputs/'):]}" if pdf.startswith("outputs/") else "",
        }

    return {
        "id": story_id,
        "path": rel,
        "episode": data,
        "bridges": bridges,
        "assembly": assembly,
        "assembly_image_only": assembly_image_only,
    }
