"""Comics-only catalog for public reviewers (no stats / ROI / admin fields)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from comicengine.config import OUTPUTS, ROOT
from comicengine.library import load_catalog
from comicengine.stories import load_story

# Primary genre + tags for reader filter/sort. Lower sort_rank floats first.
STORY_TAXONOMY: dict[str, dict[str, Any]] = {
    "episode_how_i_met_your_mother_ep1": {
        "genre": "romance",
        "tags": ["romance", "drama", "comedy"],
        "sort_rank": 0,
    },
    "episode_cjp_origin": {
        "genre": "politics",
        "tags": ["politics", "drama", "education"],
        "sort_rank": 20,
    },
    "episode_et_tu_brutus": {
        "genre": "history",
        "tags": ["history", "politics", "drama"],
        "sort_rank": 30,
    },
    "episode_hitler_warning": {
        "genre": "history",
        "tags": ["history", "politics", "drama"],
        "sort_rank": 40,
    },
}

GENRE_ORDER = ("romance", "politics", "history")


def taxonomy_for(story_id: str) -> dict[str, Any]:
    meta = STORY_TAXONOMY.get(story_id) or {}
    genre = str(meta.get("genre") or "other")
    tags = list(meta.get("tags") or [genre])
    return {
        "genre": genre,
        "tags": tags,
        "sort_rank": int(meta.get("sort_rank", 100)),
    }


def public_stories() -> dict[str, Any]:
    catalog = load_catalog(refresh=False)
    # Prefer the same library heroes as Vercel thumbnails
    hero_panel = {
        "episode_cjp_origin": 5,
        "episode_et_tu_brutus": 11,
        "episode_hitler_warning": 1,
        "episode_how_i_met_your_mother_ep1": 7,  # bubble-free Rohan + Elena lobby two-shot
    }
    stories_out: list[dict[str, Any]] = []
    for s in catalog.get("stories") or []:
        sid = s["id"]
        if "__" in sid:
            continue  # skip phase-collision aliases
        eds = s.get("editions") or {}
        reader = eds.get("reader") or {}
        if reader.get("available") is False and not (eds.get("image_only") or {}).get("available"):
            continue
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
        tax = taxonomy_for(sid)
        stories_out.append(
            {
                "id": sid,
                "title": s.get("title") or ep.get("title") or sid,
                "topic": s.get("topic") or ep.get("topic") or "",
                "panel_count": len(panels) or s.get("panel_count") or 0,
                "genre": tax["genre"],
                "tags": tax["tags"],
                "sort_rank": tax["sort_rank"],
                "webtoon_href": reader.get("webtoon_href"),
                "pdf_href": reader.get("pdf_href"),
                "thumbnail_href": thumb,
                "thumbnail_panel": want,
                "reader_href": f"/review/{sid}",
                "panels": panels,
            }
        )
    stories_out.sort(
        key=lambda x: (
            int(x["sort_rank"]) if x.get("sort_rank") is not None else 100,
            (x.get("title") or "").lower(),
        )
    )
    return {
        "count": len(stories_out),
        "stories": stories_out,
        "mode": "public_review",
        "genres": list(GENRE_ORDER),
        "tags": sorted({t for s in stories_out for t in (s.get("tags") or [])}),
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
                "genre": s.get("genre") or "other",
                "tags": list(s.get("tags") or []),
                "sort_rank": int(s["sort_rank"]) if s.get("sort_rank") is not None else 100,
                "pdf": f"/comics/{sid}/episode.pdf",
                "webtoon": f"/comics/{sid}/webtoon.png",
                "thumbnail": f"/comics/{sid}/thumbnail.jpg",
                "panels": panels,
            }
        )
    slim.sort(
        key=lambda x: (
            int(x["sort_rank"]) if x.get("sort_rank") is not None else 100,
            (x.get("title") or "").lower(),
        )
    )
    out = {
        "stories": slim,
        "count": len(slim),
        "genres": list(data.get("genres") or GENRE_ORDER),
        "tags": list(data.get("tags") or []),
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out
