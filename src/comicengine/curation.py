"""Phase 8 — curation ledger (approve / reject / regenerate) in SQLite."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Literal

from comicengine.config import OUTPUTS, ROOT, USAGE_DB_PATH
from comicengine.episode_schema import Episode
from comicengine.stories import list_stories

Status = Literal["pending", "approved", "rejected", "regenerating", "regenerated"]

CURATION_SCHEMA = """
CREATE TABLE IF NOT EXISTS curation_item (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  story_id TEXT NOT NULL,
  panel_index INTEGER,
  status TEXT NOT NULL DEFAULT 'pending',
  note TEXT DEFAULT '',
  rating INTEGER,
  suggestions TEXT DEFAULT '',
  updated_at TEXT NOT NULL,
  meta_json TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_curation_story ON curation_item(story_id);
CREATE INDEX IF NOT EXISTS idx_curation_status ON curation_item(status);
"""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _item_id(story_id: str, panel_index: int | None = None) -> str:
    if panel_index is None:
        return f"episode:{story_id}"
    return f"panel:{story_id}:{int(panel_index)}"


class CurationDB:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or USAGE_DB_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init(self) -> None:
        with self.connect() as conn:
            conn.executescript(CURATION_SCHEMA)
            cols = {r["name"] for r in conn.execute("PRAGMA table_info(curation_item)").fetchall()}
            if "rating" not in cols:
                conn.execute("ALTER TABLE curation_item ADD COLUMN rating INTEGER")
            if "suggestions" not in cols:
                conn.execute("ALTER TABLE curation_item ADD COLUMN suggestions TEXT DEFAULT ''")

    def upsert(
        self,
        *,
        story_id: str,
        panel_index: int | None = None,
        status: Status | None = None,
        note: str | None = None,
        rating: int | None = None,
        suggestions: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        kind = "episode" if panel_index is None else "panel"
        cid = _item_id(story_id, panel_index)
        now = _utcnow()
        existing = self.get(cid)
        new_status = status or (existing["status"] if existing else "pending")
        new_note = note if note is not None else (existing["note"] if existing else "")
        new_rating = rating if rating is not None else (existing.get("rating") if existing else None)
        if new_rating is not None:
            new_rating = max(1, min(5, int(new_rating)))
        new_suggestions = (
            suggestions
            if suggestions is not None
            else (existing.get("suggestions") if existing else "")
        )
        new_meta = dict(existing["meta"] if existing else {})
        if meta:
            new_meta.update(meta)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO curation_item(
                  id, kind, story_id, panel_index, status, note, rating, suggestions, updated_at, meta_json
                )
                VALUES(?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                  status=excluded.status,
                  note=excluded.note,
                  rating=excluded.rating,
                  suggestions=excluded.suggestions,
                  updated_at=excluded.updated_at,
                  meta_json=excluded.meta_json
                """,
                (
                    cid,
                    kind,
                    story_id,
                    panel_index,
                    new_status,
                    new_note,
                    new_rating,
                    new_suggestions or "",
                    now,
                    json.dumps(new_meta),
                ),
            )
        return self.get(cid) or {}

    def get(self, item_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM curation_item WHERE id=?", (item_id,)).fetchone()
        return self._row(row) if row else None

    def list(
        self,
        *,
        story_id: str | None = None,
        status: str | None = None,
        kind: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        args: list[Any] = []
        if story_id:
            clauses.append("story_id=?")
            args.append(story_id)
        if status:
            clauses.append("status=?")
            args.append(status)
        if kind:
            clauses.append("kind=?")
            args.append(kind)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM curation_item {where} ORDER BY story_id, kind, panel_index",
                args,
            ).fetchall()
        return [self._row(r) for r in rows]

    def summary(self) -> dict[str, Any]:
        with self.connect() as conn:
            by_status = [
                dict(r)
                for r in conn.execute(
                    "SELECT status, COUNT(*) AS n FROM curation_item GROUP BY status ORDER BY n DESC"
                )
            ]
            by_story = [
                dict(r)
                for r in conn.execute(
                    """
                    SELECT story_id,
                           SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) AS approved,
                           SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) AS rejected,
                           SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pending,
                           SUM(CASE WHEN status IN ('regenerating','regenerated') THEN 1 ELSE 0 END) AS regen,
                           COUNT(*) AS total
                    FROM curation_item
                    GROUP BY story_id
                    ORDER BY story_id
                    """
                )
            ]
            total = conn.execute("SELECT COUNT(*) AS n FROM curation_item").fetchone()["n"]
        return {"total": total, "by_status": by_status, "by_story": by_story}

    def seed_from_stories(self) -> dict[str, Any]:
        """Ensure episode + panel rows exist (pending) for discovered episode JSON."""
        created = 0
        for story in list_stories():
            sid = story["id"]
            if not self.get(_item_id(sid)):
                self.upsert(story_id=sid, status="pending", note="seeded")
                created += 1
            path = ROOT / story["path"] if not Path(story["path"]).is_absolute() else Path(story["path"])
            if not path.is_file():
                # try under repo root relative
                path = ROOT / story["path"]
            if not path.is_file():
                continue
            episode = Episode.model_validate(json.loads(path.read_text()))
            for panel in episode.panels:
                cid = _item_id(sid, panel.index)
                if not self.get(cid):
                    self.upsert(
                        story_id=sid,
                        panel_index=panel.index,
                        status="pending",
                        note="seeded",
                        meta={
                            "image_path": panel.image_path,
                            "composed_image_path": panel.composed_image_path,
                        },
                    )
                    created += 1
        return {"created": created, "summary": self.summary()}

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        try:
            d["meta"] = json.loads(d.pop("meta_json") or "{}")
        except json.JSONDecodeError:
            d["meta"] = {}
        d["rating"] = d.get("rating")
        d["suggestions"] = d.get("suggestions") or ""
        return d


curation = CurationDB()


def episode_json_path(story_id: str) -> Path | None:
    for story in list_stories():
        if story["id"] == story_id:
            p = ROOT / story["path"]
            return p if p.is_file() else None
    for cand in [
        OUTPUTS / "phase0.5" / f"{story_id}.json",
        OUTPUTS / "phase4" / f"{story_id}.json",
    ]:
        if cand.is_file():
            return cand
    return None


def panel_editor_payload(story_id: str, panel_index: int) -> dict[str, Any]:
    """Current prompt + dialogue/caption for the regenerate editor."""
    path = episode_json_path(story_id)
    if not path:
        raise FileNotFoundError(f"episode JSON not found for {story_id}")
    episode = Episode.model_validate(json.loads(path.read_text()))
    panel = next((p for p in episode.panels if p.index == panel_index), None)
    if not panel:
        raise ValueError(f"panel {panel_index} missing in {story_id}")
    item = curation.get(_item_id(story_id, panel_index)) or {}
    return {
        "story_id": story_id,
        "panel_index": panel_index,
        "title": episode.title,
        "scene_description": panel.scene_description,
        "art_prompt": panel.art_prompt,
        "dialogue": panel.dialogue,
        "caption": panel.caption,
        "emotion": panel.emotion,
        "characters": panel.characters,
        "image_path": panel.image_path,
        "composed_image_path": panel.composed_image_path,
        "rating": item.get("rating"),
        "suggestions": item.get("suggestions") or "",
        "status": item.get("status") or "pending",
        "note": item.get("note") or "",
        "prior_prompt": (item.get("meta") or {}).get("last_prompt") or panel.art_prompt,
    }


def regenerate_panel(
    story_id: str,
    panel_index: int,
    *,
    note: str = "",
    prompt: str | None = None,
    rating: int | None = None,
    suggestions: str | None = None,
    mark_rejected_first: bool = False,
) -> dict[str, Any]:
    """Re-render one panel with optional user-edited prompt + recompose bubbles."""
    from comicengine.clients import TrackedClients
    from comicengine.compositor import compose_panel
    from comicengine.library import rebuild_catalog
    from comicengine.panel_batch import (
        PHASE5,
        char_lookup,
        ensure_ref,
        load_episode,
        render_panel,
    )

    path = episode_json_path(story_id)
    if not path:
        raise FileNotFoundError(f"episode JSON not found for {story_id}")

    if mark_rejected_first:
        curation.upsert(
            story_id=story_id,
            panel_index=panel_index,
            status="rejected",
            note=note or "rejected before regen",
            rating=rating,
            suggestions=suggestions,
        )

    curation.upsert(
        story_id=story_id,
        panel_index=panel_index,
        status="regenerating",
        note=note or "regenerate requested",
        rating=rating,
        suggestions=suggestions,
    )

    episode = load_episode(path)
    panel = next((p for p in episode.panels if p.index == panel_index), None)
    if not panel:
        raise ValueError(f"panel {panel_index} missing in {story_id}")

    edited = (prompt or "").strip()
    if edited:
        panel.art_prompt = edited

    clients = TrackedClients(phase="phase8.5")
    refs: dict[str, Path] = {}
    lookup = char_lookup(episode)
    needed = set(panel.characters) | {c.id for c in episode.characters}
    for cid in needed:
        char = lookup.get(cid)
        if not char:
            continue
        try:
            ref = ensure_ref(clients, char, skip_existing=True)
            if ref:
                refs[cid] = ref
        except Exception:  # noqa: BLE001
            continue

    out_path = PHASE5 / story_id / f"panel_{panel_index:02d}.png"
    row = render_panel(
        clients,
        episode,
        panel_index,
        out_path=out_path,
        refs=refs,
        skip_existing=False,
        max_retries=2,
        prompt_override=edited or None,
    )
    if row.get("status") not in {"ok", "skipped_existing"}:
        curation.upsert(
            story_id=story_id,
            panel_index=panel_index,
            status="rejected",
            note=f"regen failed: {row.get('error')}",
            rating=rating,
            suggestions=suggestions,
            meta={"regen": row},
        )
        raise RuntimeError(row.get("error") or "regenerate failed")

    panel.image_path = str(out_path.relative_to(ROOT))
    panel.image_method = str(row.get("method") or "")
    panel.image_qa = str((row.get("qa") or {}).get("verdict") or "")

    composed_path = OUTPUTS / "phase6" / story_id / f"panel_{panel_index:02d}.png"
    compose_panel(panel, out_path, composed_path)
    panel.composed_image_path = str(composed_path.relative_to(ROOT))
    path.write_text(episode.model_dump_json(indent=2))

    item = curation.upsert(
        story_id=story_id,
        panel_index=panel_index,
        status="regenerated",
        note=note or "regenerated with user prompt" if edited else "regenerated",
        rating=rating,
        suggestions=suggestions,
        meta={
            "method": row.get("method"),
            "image_path": panel.image_path,
            "composed_image_path": panel.composed_image_path,
            "qa": panel.image_qa,
            "last_prompt": panel.art_prompt,
            "prompt_edited": bool(edited),
        },
    )
    try:
        rebuild_catalog()
    except Exception:  # noqa: BLE001
        pass
    return {
        "ok": True,
        "item": item,
        "render": row,
        "composed": str(composed_path),
        "art_prompt": panel.art_prompt,
        "image_href": f"/media/phase6/{story_id}/panel_{panel_index:02d}.png?v={item.get('updated_at')}",
    }
