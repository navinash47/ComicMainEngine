from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from comicengine.config import USAGE_DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS api_call (
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL,
  phase TEXT,
  provider TEXT NOT NULL,
  model TEXT,
  purpose TEXT,
  input_tokens INTEGER DEFAULT 0,
  output_tokens INTEGER DEFAULT 0,
  image_tokens INTEGER DEFAULT 0,
  cost_usd REAL DEFAULT 0,
  latency_ms INTEGER DEFAULT 0,
  ok INTEGER DEFAULT 1,
  error TEXT,
  meta_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_api_call_ts ON api_call(ts);
CREATE INDEX IF NOT EXISTS idx_api_call_provider ON api_call(provider);
CREATE INDEX IF NOT EXISTS idx_api_call_phase ON api_call(phase);
"""


@dataclass
class ApiCall:
    provider: str
    model: str = ""
    purpose: str = ""
    phase: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    image_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    ok: bool = True
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class UsageDB:
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

    def log(self, call: ApiCall) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO api_call (
                  ts, phase, provider, model, purpose,
                  input_tokens, output_tokens, image_tokens,
                  cost_usd, latency_ms, ok, error, meta_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _utcnow(),
                    call.phase,
                    call.provider,
                    call.model,
                    call.purpose,
                    call.input_tokens,
                    call.output_tokens,
                    call.image_tokens,
                    call.cost_usd,
                    call.latency_ms,
                    1 if call.ok else 0,
                    call.error,
                    json.dumps(call.meta or {}),
                ),
            )
            return int(cur.lastrowid)

    def summary(self) -> dict[str, Any]:
        with self.connect() as conn:
            totals = conn.execute(
                """
                SELECT
                  COUNT(*) AS calls,
                  COALESCE(SUM(input_tokens),0) AS input_tokens,
                  COALESCE(SUM(output_tokens),0) AS output_tokens,
                  COALESCE(SUM(image_tokens),0) AS image_tokens,
                  COALESCE(SUM(cost_usd),0) AS cost_usd,
                  COALESCE(SUM(CASE WHEN ok=0 THEN 1 ELSE 0 END),0) AS errors
                FROM api_call
                """
            ).fetchone()
            by_provider = conn.execute(
                """
                SELECT provider,
                  COUNT(*) AS calls,
                  COALESCE(SUM(input_tokens),0) AS input_tokens,
                  COALESCE(SUM(output_tokens),0) AS output_tokens,
                  COALESCE(SUM(image_tokens),0) AS image_tokens,
                  COALESCE(SUM(cost_usd),0) AS cost_usd
                FROM api_call
                GROUP BY provider
                ORDER BY cost_usd DESC
                """
            ).fetchall()
            by_phase = conn.execute(
                """
                SELECT COALESCE(phase,'(none)') AS phase,
                  COUNT(*) AS calls,
                  COALESCE(SUM(cost_usd),0) AS cost_usd,
                  COALESCE(SUM(input_tokens+output_tokens+image_tokens),0) AS tokens
                FROM api_call
                GROUP BY phase
                ORDER BY cost_usd DESC
                """
            ).fetchall()
            by_model = conn.execute(
                """
                SELECT provider, COALESCE(model,'(unknown)') AS model,
                  COUNT(*) AS calls,
                  COALESCE(SUM(input_tokens),0) AS input_tokens,
                  COALESCE(SUM(output_tokens),0) AS output_tokens,
                  COALESCE(SUM(image_tokens),0) AS image_tokens,
                  COALESCE(SUM(cost_usd),0) AS cost_usd
                FROM api_call
                GROUP BY provider, model
                ORDER BY cost_usd DESC
                """
            ).fetchall()
            recent = conn.execute(
                """
                SELECT id, ts, phase, provider, model, purpose,
                       input_tokens, output_tokens, image_tokens,
                       cost_usd, latency_ms, ok, error
                FROM api_call
                ORDER BY id DESC
                LIMIT 50
                """
            ).fetchall()
            series = conn.execute(
                """
                SELECT substr(ts,1,16) AS minute,
                       ROUND(SUM(cost_usd), 6) AS cost_usd,
                       SUM(input_tokens+output_tokens+image_tokens) AS tokens
                FROM api_call
                GROUP BY minute
                ORDER BY minute ASC
                LIMIT 200
                """
            ).fetchall()

        def rows(rs: list[sqlite3.Row]) -> list[dict[str, Any]]:
            return [dict(r) for r in rs]

        return {
            "totals": dict(totals) if totals else {},
            "by_provider": rows(by_provider),
            "by_phase": rows(by_phase),
            "by_model": rows(by_model),
            "recent": rows(recent),
            "series": rows(series),
            "db_path": str(self.path),
            "server_time": _utcnow(),
        }


class TimedCall:
    def __init__(self, db: UsageDB, call: ApiCall) -> None:
        self.db = db
        self.call = call
        self._t0 = 0.0

    def __enter__(self) -> ApiCall:
        self._t0 = time.perf_counter()
        return self.call

    def __exit__(self, exc_type, exc, tb) -> None:
        self.call.latency_ms = int((time.perf_counter() - self._t0) * 1000)
        if exc is not None:
            self.call.ok = False
            self.call.error = f"{exc_type.__name__}: {exc}" if exc_type else str(exc)
        self.db.log(self.call)
        return False
