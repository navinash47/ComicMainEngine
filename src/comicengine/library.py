"""Story Library — catalog of UI stories + Reader / Only-Image editions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from comicengine.config import OUTPUTS, ROOT
from comicengine.curation import curation
from comicengine.stories import list_stories

LIBRARY_DIR = OUTPUTS / "library"
CATALOG_PATH = LIBRARY_DIR / "catalog.json"


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def rebuild_catalog() -> dict[str, Any]:
    """Scan stories + Phase 7 / 7.5 manifests into outputs/library/catalog.json."""
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    for story in list_stories():
        sid = story["id"]
        composed = _load_manifest(OUTPUTS / "phase7" / sid / "manifest.json")
        image_only = _load_manifest(OUTPUTS / "phase7.5" / sid / "manifest.json")
        cur_items = curation.list(story_id=sid)
        cur_summary = {
            "approved": sum(1 for i in cur_items if i["status"] == "approved"),
            "rejected": sum(1 for i in cur_items if i["status"] == "rejected"),
            "pending": sum(1 for i in cur_items if i["status"] == "pending"),
            "regenerated": sum(1 for i in cur_items if i["status"] in {"regenerated", "regenerating"}),
            "total": len(cur_items),
            "panels": [
                {
                    "index": i.get("panel_index"),
                    "status": i.get("status"),
                    "note": i.get("note") or "",
                    "rating": i.get("rating"),
                    "suggestions": i.get("suggestions") or "",
                    "updated_at": i.get("updated_at"),
                }
                for i in cur_items
                if i.get("kind") == "panel"
            ],
            "avg_rating": (
                round(
                    sum(i.get("rating") or 0 for i in cur_items if i.get("kind") == "panel" and i.get("rating"))
                    / max(
                        sum(1 for i in cur_items if i.get("kind") == "panel" and i.get("rating")),
                        1,
                    ),
                    2,
                )
                if any(i.get("kind") == "panel" and i.get("rating") for i in cur_items)
                else None
            ),
            "episode_status": next(
                (i.get("status") for i in cur_items if i.get("kind") == "episode"),
                "pending",
            ),
        }
        entries.append(
            {
                "id": sid,
                "title": story.get("title") or sid,
                "topic": story.get("topic") or "",
                "voice": story.get("voice") or "",
                "panel_count": story.get("panel_count") or 0,
                "phase": story.get("phase") or "",
                "path": story.get("path") or "",
                "reader_href": story.get("href") or f"/stories/{sid}",
                "json_href": story.get("json_href") or f"/api/stories/{sid}",
                "disclaimer": story.get("disclaimer") or "",
                "curation": cur_summary,
                "editions": {
                    "reader": {
                        "label": "Reader (bubbles + captions)",
                        "phase": "phase7",
                        "available": bool(composed.get("webtoon_href") or composed.get("pdf_href")),
                        "webtoon_href": composed.get("webtoon_href")
                        or (f"/media/phase7/{sid}/webtoon.png" if composed else None),
                        "pdf_href": composed.get("pdf_href")
                        or (f"/media/phase7/{sid}/episode.pdf" if composed else None),
                        "webtoon_path": composed.get("webtoon_path"),
                        "pdf_path": composed.get("pdf_path"),
                        "assembled_panels": composed.get("assembled_panels"),
                    },
                    "image_only": {
                        "label": "Only Image (no bubbles)",
                        "phase": "phase7.5",
                        "available": bool(image_only.get("webtoon_href") or image_only.get("pdf_href")),
                        "webtoon_href": image_only.get("webtoon_href")
                        or (
                            f"/media/phase7.5/{sid}/webtoon_image_only.png" if image_only else None
                        ),
                        "pdf_href": image_only.get("pdf_href")
                        or (
                            f"/media/phase7.5/{sid}/episode_image_only.pdf" if image_only else None
                        ),
                        "webtoon_path": image_only.get("webtoon_path"),
                        "pdf_path": image_only.get("pdf_path"),
                        "assembled_panels": image_only.get("assembled_panels"),
                    },
                },
            }
        )

    catalog = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(entries),
        "stories": entries,
        "curation_summary": curation.summary(),
        "store_path": str(CATALOG_PATH.relative_to(ROOT)),
        "notes": (
            "Story Library stores dashboard editions: Reader (Phase 7 composed) "
            "and Only Image (Phase 7.5 raw panels), plus Phase 8/8.5 curation "
            "(status, rating, suggestions)."
        ),
    }
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2))
    return catalog


def load_catalog(*, refresh: bool = False) -> dict[str, Any]:
    if refresh or not CATALOG_PATH.is_file():
        return rebuild_catalog()
    try:
        data = json.loads(CATALOG_PATH.read_text())
        if isinstance(data, dict) and "stories" in data:
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return rebuild_catalog()
