"""Local image gallery — generated outputs + free Commons reference packs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from comicengine.config import OUTPUTS, ROOT

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif"}
REFS_MANIFEST = OUTPUTS / "phase0.5" / "refs" / "manifest.json"


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def list_generated() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not OUTPUTS.exists():
        return items
    for path in sorted(OUTPUTS.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTS:
            continue
        # skip giant originals preferred — show all under outputs
        if "refs" in path.parts:
            continue
        rel = _rel(path)
        items.append(
            {
                "id": path.stem,
                "title": path.name,
                "phase": path.parent.name,
                "path": rel,
                "href": f"/media/{rel.removeprefix('outputs/')}",
                "source": "generated",
                "bytes": path.stat().st_size,
            }
        )
    return items


def list_cjp_refs() -> list[dict[str, Any]]:
    if not REFS_MANIFEST.exists():
        return []
    try:
        data = json.loads(REFS_MANIFEST.read_text())
    except json.JSONDecodeError:
        return []
    items = []
    for row in data.get("images") or []:
        local = ROOT / row["local_path"] if not Path(row["local_path"]).is_absolute() else Path(row["local_path"])
        if not local.is_file():
            continue
        rel = _rel(local)
        items.append(
            {
                "id": row.get("id") or local.stem,
                "title": row.get("title") or local.name,
                "role": row.get("role") or "reference",
                "path": rel,
                "href": f"/media/{rel.removeprefix('outputs/')}",
                "source": "commons",
                "license": row.get("license"),
                "artist": row.get("artist"),
                "commons_url": row.get("commons_url"),
                "note": row.get("note") or "",
            }
        )
    return items


def gallery() -> dict[str, Any]:
    return {
        "generated": list_generated(),
        "cjp_refs": list_cjp_refs(),
        "attribution": (
            "CJP reference photos are free Wikimedia Commons files (CC/Public Domain). "
            "They illustrate place/atmosphere for the bedtime test comic — not official CJP media."
        ),
    }
