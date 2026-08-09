"""Name-based per-story + per-panel feedback (public reviewers)."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from comicengine.config import USAGE_DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS story_feedback (
  id TEXT PRIMARY KEY,
  reviewer_key TEXT NOT NULL,
  reviewer_name TEXT NOT NULL,
  story_id TEXT NOT NULL,
  overall_rating INTEGER NOT NULL,
  overall_feedback TEXT DEFAULT '',
  panels_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  user_agent TEXT DEFAULT '',
  meta_json TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_story_fb_story ON story_feedback(story_id);
CREATE INDEX IF NOT EXISTS idx_story_fb_name ON story_feedback(reviewer_name);
"""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def name_key(name: str) -> str:
    cleaned = " ".join(name.strip().split())
    return "name:" + hashlib.sha256(cleaned.lower().encode()).hexdigest()[:16]


class StoryFeedbackDB:
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
            conn.executescript(SCHEMA)

    def submit(
        self,
        *,
        name: str,
        story_id: str,
        overall_rating: int,
        overall_feedback: str = "",
        panels: list[dict[str, Any]] | None = None,
        user_agent: str = "",
    ) -> dict[str, Any]:
        name = " ".join((name or "").strip().split())
        if not name:
            raise ValueError("name required")
        if not story_id:
            raise ValueError("story_id required")
        rating = int(overall_rating)
        if not (1 <= rating <= 5):
            raise ValueError("overall_rating must be 1–5")

        cleaned_panels: list[dict[str, Any]] = []
        for p in panels or []:
            try:
                idx = int(p.get("index"))
            except (TypeError, ValueError):
                continue
            try:
                pr = int(p.get("rating"))
            except (TypeError, ValueError):
                continue
            if not (1 <= pr <= 5):
                continue
            cleaned_panels.append(
                {
                    "index": idx,
                    "rating": pr,
                    "feedback": str(p.get("feedback") or "").strip()[:2000],
                }
            )

        rid = str(uuid.uuid4())
        now = _utcnow()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO story_feedback(
                  id, reviewer_key, reviewer_name, story_id,
                  overall_rating, overall_feedback, panels_json,
                  created_at, user_agent, meta_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    rid,
                    name_key(name),
                    name,
                    story_id,
                    rating,
                    (overall_feedback or "").strip()[:4000],
                    json.dumps(cleaned_panels, ensure_ascii=False),
                    now,
                    user_agent[:500],
                    "{}",
                ),
            )
        try:
            from comicengine.usage import UsageDB

            UsageDB().log_local(
                phase="phase8.6",
                purpose="story_feedback",
                note=f"{name} reviewed {story_id}",
                meta={"story_id": story_id, "overall_rating": rating, "panels": len(cleaned_panels)},
            )
        except Exception:  # noqa: BLE001
            pass
        return self.get(rid) or {}

    def get(self, response_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM story_feedback WHERE id=?", (response_id,)
            ).fetchone()
        return self._row(row) if row else None

    def list(self, *, story_id: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
        sql = "SELECT * FROM story_feedback WHERE 1=1"
        args: list[Any] = []
        if story_id:
            sql += " AND story_id=?"
            args.append(story_id)
        sql += " ORDER BY created_at DESC LIMIT ?"
        args.append(limit)
        with self.connect() as conn:
            rows = conn.execute(sql, args).fetchall()
        return [self._row(r) for r in rows]

    def summary(self) -> dict[str, Any]:
        with self.connect() as conn:
            total = conn.execute("SELECT COUNT(*) AS n FROM story_feedback").fetchone()["n"]
            people = conn.execute(
                "SELECT COUNT(DISTINCT reviewer_key) AS n FROM story_feedback"
            ).fetchone()["n"]
            by_story = [
                dict(r)
                for r in conn.execute(
                    """
                    SELECT story_id, COUNT(*) AS n, AVG(overall_rating) AS avg_rating
                    FROM story_feedback GROUP BY story_id ORDER BY n DESC
                    """
                ).fetchall()
            ]
        return {"responses": total, "reviewers": people, "by_story": by_story}

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        try:
            d["panels"] = json.loads(d.pop("panels_json") or "[]")
        except json.JSONDecodeError:
            d["panels"] = []
        try:
            d["meta"] = json.loads(d.pop("meta_json") or "{}")
        except json.JSONDecodeError:
            d["meta"] = {}
        return d


story_feedback = StoryFeedbackDB()
