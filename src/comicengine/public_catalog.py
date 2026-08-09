"""Comics-only catalog for public reviewers (no stats / ROI / admin fields)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from comicengine.config import OUTPUTS, ROOT
from comicengine.library import load_catalog
from comicengine.stories import load_story


def public_stories() -> dict[str, Any]:
    catalog = load_catalog(refresh=False)
    # Prefer the same library heroes as Vercel thumbnails
    hero_panel = {
        "episode_cjp_origin": 5,
        "episode_et_tu_brutus": 11,
        "episode_hitler_warning": 1,
    }
    stories_out: list[dict[str, Any]] = []
    for s in catalog.get("stories") or []:
        sid = s["id"]
        full = load_story(sid) or {}
        ep = full.get("episode") or {}
        panels = []
        for p in ep.get("panels") or []:
            if not isinstance(p, dict):
                continue
            href = p.get("image_href") or ""
            panels.append(
                {
                    "index": p.get("index"),
                    "scene_description": p.get("scene_description") or "",
                    "dialogue": p.get("dialogue") or "",
                    "caption": p.get("caption") or "",
                    "image_href": href,
                }
            )
        eds = s.get("editions") or {}
        reader = eds.get("reader") or {}
        thumb = ""
        want = hero_panel.get(sid)
        if want:
            hit = next((p for p in panels if int(p.get("index") or 0) == want), None)
            if hit and hit.get("image_href"):
                thumb = hit["image_href"]
        if not thumb and panels:
            thumb = panels[0].get("image_href") or ""
        if not thumb:
            thumb = reader.get("webtoon_href") or ""
        stories_out.append(
            {
                "id": sid,
                "title": s.get("title") or ep.get("title") or sid,
                "topic": s.get("topic") or ep.get("topic") or "",
                "panel_count": len(panels) or s.get("panel_count") or 0,
                "webtoon_href": reader.get("webtoon_href"),
                "pdf_href": reader.get("pdf_href"),
                "thumbnail_href": thumb,
                "thumbnail_panel": want,
                "reader_href": f"/review/{sid}",
                "panels": panels,
            }
        )
    return {
        "count": len(stories_out),
        "stories": stories_out,
        "mode": "public_review",
    }


def write_vercel_manifest(dest: Path) -> dict[str, Any]:
    """Copy slim story metadata for the Vercel review app (media under /comics)."""
    data = public_stories()
    slim = []
    for s in data["stories"]:
        sid = s["id"]
        panels = []
        for p in s["panels"]:
            idx = int(p["index"])
            panels.append(
                {
                    "index": idx,
                    "scene_description": p.get("scene_description") or "",
                    "dialogue": p.get("dialogue") or "",
                    "caption": p.get("caption") or "",
                    "image": f"/comics/{sid}/panel_{idx:02d}.png",
                }
            )
        slim.append(
            {
                "id": sid,
                "title": s["title"],
                "topic": s["topic"],
                "panel_count": len(panels),
                "pdf": f"/comics/{sid}/episode.pdf",
                "webtoon": f"/comics/{sid}/webtoon.png",
                "thumbnail": f"/comics/{sid}/thumbnail.jpg",
                "panels": panels,
            }
        )
    out = {"stories": slim, "count": len(slim)}
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out
