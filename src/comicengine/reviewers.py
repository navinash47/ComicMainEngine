"""Phase 8.6 — reviewer / people ledger (Google identities)."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from comicengine.config import ADMIN_EMAILS, USAGE_DB_PATH

REVIEWER_SCHEMA = """
CREATE TABLE IF NOT EXISTS reviewer (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL,
  name TEXT DEFAULT '',
  picture TEXT DEFAULT '',
  locale TEXT DEFAULT '',
  is_admin INTEGER NOT NULL DEFAULT 0,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  login_count INTEGER NOT NULL DEFAULT 1,
  meta_json TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_reviewer_email ON reviewer(email);
"""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReviewerDB:
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
            conn.executescript(REVIEWER_SCHEMA)

    def upsert_from_google(self, profile: dict[str, Any]) -> dict[str, Any]:
        sub = str(profile.get("sub") or profile.get("id") or "").strip()
        email = str(profile.get("email") or "").strip().lower()
        if not sub or not email:
            raise ValueError("Google profile missing sub/email")
        name = str(profile.get("name") or profile.get("given_name") or email)
        picture = str(profile.get("picture") or "")
        locale = str(profile.get("locale") or "")
        now = _utcnow()
        is_admin = 1 if email in ADMIN_EMAILS else 0
        existing = self.get(sub)
        with self.connect() as conn:
            if existing:
                conn.execute(
                    """
                    UPDATE reviewer SET
                      email=?, name=?, picture=?, locale=?,
                      is_admin=CASE WHEN ? > is_admin THEN ? ELSE is_admin END,
                      last_seen_at=?,
                      login_count=login_count+1
                    WHERE id=?
                    """,
                    (email, name, picture, locale, is_admin, is_admin, now, sub),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO reviewer(
                      id, email, name, picture, locale, is_admin,
                      first_seen_at, last_seen_at, login_count, meta_json
                    ) VALUES(?,?,?,?,?,?,?,?,1,'{}')
                    """,
                    (sub, email, name, picture, locale, is_admin, now, now),
                )
        return self.get(sub) or {}

    def get(self, reviewer_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM reviewer WHERE id=?", (reviewer_id,)
            ).fetchone()
        return self._row(row) if row else None

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM reviewer WHERE email=?", (email.strip().lower(),)
            ).fetchone()
        return self._row(row) if row else None

    def list(self, *, limit: int = 500) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM reviewer ORDER BY last_seen_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row(r) for r in rows]

    def summary(self) -> dict[str, Any]:
        with self.connect() as conn:
            total = conn.execute("SELECT COUNT(*) AS n FROM reviewer").fetchone()["n"]
            admins = conn.execute(
                "SELECT COUNT(*) AS n FROM reviewer WHERE is_admin=1"
            ).fetchone()["n"]
        return {"reviewers": total, "admins": admins}

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        try:
            d["meta"] = json.loads(d.pop("meta_json") or "{}")
        except json.JSONDecodeError:
            d["meta"] = {}
        d["is_admin"] = bool(d.get("is_admin"))
        return d


reviewers = ReviewerDB()
