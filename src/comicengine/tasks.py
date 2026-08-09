"""Global TaskObserver — one SQLite-backed task board shared by scripts + dashboard."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Literal

from comicengine.config import OUTPUTS, USAGE_DB_PATH

Status = Literal["pending", "in_progress", "completed", "failed", "blocked"]

TASK_SCHEMA = """
CREATE TABLE IF NOT EXISTS task (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT DEFAULT '',
  status TEXT NOT NULL DEFAULT 'pending',
  progress REAL NOT NULL DEFAULT 0,
  sort_order INTEGER NOT NULL DEFAULT 0,
  phase TEXT DEFAULT '',
  updated_at TEXT NOT NULL,
  meta_json TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_task_status ON task(status);
CREATE INDEX IF NOT EXISTS idx_task_sort ON task(sort_order);
"""

# Canonical ComicEngine roadmap — stable IDs so every process updates the same rows
DEFAULT_TASKS: list[dict[str, Any]] = [
    {"id": "phase0", "title": "Phase 0 — Environments & accounts", "phase": "phase0", "sort_order": 0,
     "description": "venv, .env keys, API hello pings"},
    {"id": "phase0.5", "title": "Phase 0.5 — AI script engine (test episode)", "phase": "phase0.5", "sort_order": 7,
     "description": "Bedtime CJP origin episode JSON via Claude"},
    {"id": "phase1", "title": "Phase 1 — Single-image generation", "phase": "phase1", "sort_order": 10,
     "description": "Nano Banana hello image (+ local FLUX later on PC)"},
    {"id": "phase2", "title": "Phase 2 — Style lock", "phase": "phase2", "sort_order": 20,
     "description": "Style suffix + small grid + style_anchor.png"},
    {"id": "phase3", "title": "Phase 3 — Character consistency bake-off", "phase": "phase3", "sort_order": 30,
     "description": "Dad / Daughter / figure rubric"},
    {"id": "phase4", "title": "Phase 4 — Multi-topic LLM scripts", "phase": "phase4", "sort_order": 40,
     "description": "Et tu Brutus + Hitler warning scripts beside CJP"},
    {"id": "phase5", "title": "Phase 5 — Panel batch generator", "phase": "phase5", "sort_order": 50,
     "description": "Episode JSON → panels with gemini_ref + retries"},
    {"id": "phase6", "title": "Phase 6 — Speech bubble compositor", "phase": "phase6", "sort_order": 60,
     "description": "Pillow bubbles/captions + story reader narration"},
    {"id": "phase7", "title": "Phase 7 — Episode assembler", "phase": "phase7", "sort_order": 70,
     "description": "Vertical webtoon PNG + multi-page PDF"},
    {"id": "phase7.5", "title": "Phase 7.5 — Only Image + Story Library", "phase": "phase7.5", "sort_order": 75,
     "description": "Bubble-free webtoon/PDF + Library catalog"},
    {"id": "phase8", "title": "Phase 8 — Curation CLI + SQLite", "phase": "phase8", "sort_order": 80,
     "description": "Approve / reject / regenerate + Library UI"},
    {"id": "phase8.5", "title": "Phase 8.5 — Panel rating + prompt editor", "phase": "phase8.5", "sort_order": 85,
     "description": "Per-panel rating/suggestions; editable prompt on reject/regen; live refresh"},
    {"id": "phase8.6", "title": "Phase 8.6 — Google auth + Mom Test feedback", "phase": "phase8.6", "sort_order": 86,
     "description": "Google login, reviewer ledger, Mom Test questionnaire, feedback export"},
    {"id": "phase9", "title": "Phase 9 — ROI dashboard", "phase": "phase9", "sort_order": 90,
     "description": "/roi cost unit-economics + charts"},
    {"id": "phase10", "title": "Phase 10 — Publishing pipeline", "phase": "phase10", "sort_order": 100,
     "description": "Cloudflare Pages + R2 export of Library editions"},
    {"id": "phase11", "title": "Phase 11 — Cost optimization", "phase": "phase11", "sort_order": 110,
     "description": "Beta cost guardrails; Version 2 starts at phase12"},
    {"id": "dashboard", "title": "Live usage + TaskObserver", "phase": "dashboard", "sort_order": 5,
     "description": "Local webpage tracking tokens/cost/tasks"},
    # How I Met Your Mother — romance pipeline (stepper on dashboard)
    {"id": "phase_romance_step1", "title": "Romance Step 1 — Infatuation script",
     "phase": "phase_romance_step1", "sort_order": 200,
     "description": "Dad→daughter HIMYM Ep1 love story (butterflies, Maya teasing)"},
    {"id": "phase_romance_step2", "title": "Romance Step 2 — Manhwa character refs",
     "phase": "phase_romance_step2", "sort_order": 210,
     "description": "Rohan / Elena / Maya / Dad / friends reference sheets"},
    {"id": "phase_romance_step3", "title": "Romance Step 3 — Manhwa panel batch",
     "phase": "phase_romance_step3", "sort_order": 220,
     "description": "Episode panels with gemini_ref + feeling art prompts"},
    {"id": "phase_romance_step4", "title": "Romance Step 4 — Speech bubbles",
     "phase": "phase_romance_step4", "sort_order": 230,
     "description": "Compose dialogue/captions on panels"},
    {"id": "phase_romance_step5", "title": "Romance Step 5 — Assemble + Library",
     "phase": "phase_romance_step5", "sort_order": 240,
     "description": "Webtoon/PDF + catalog entry"},
]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Task:
    id: str
    title: str
    description: str = ""
    status: str = "pending"
    progress: float = 0.0
    sort_order: int = 0
    phase: str = ""
    updated_at: str = ""
    meta: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "progress": self.progress,
            "sort_order": self.sort_order,
            "phase": self.phase,
            "updated_at": self.updated_at,
            "meta": self.meta or {},
        }


class TaskObserver:
    """Process-safe global board. Any script/dashboard instance shares `data/usage.db`."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or USAGE_DB_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()
        self.ensure_defaults()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init(self) -> None:
        with self.connect() as conn:
            conn.executescript(TASK_SCHEMA)

    def ensure_defaults(self) -> None:
        now = _utcnow()
        with self.connect() as conn:
            for t in DEFAULT_TASKS:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO task
                      (id, title, description, status, progress, sort_order, phase, updated_at, meta_json)
                    VALUES (?, ?, ?, 'pending', 0, ?, ?, ?, '{}')
                    """,
                    (t["id"], t["title"], t["description"], t["sort_order"], t["phase"], now),
                )

    def upsert(
        self,
        task_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        status: Status | None = None,
        progress: float | None = None,
        phase: str | None = None,
        sort_order: int | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Task:
        existing = self.get(task_id)
        now = _utcnow()
        if existing is None:
            t = Task(
                id=task_id,
                title=title or task_id,
                description=description or "",
                status=status or "pending",
                progress=float(progress or 0),
                sort_order=int(sort_order or 0),
                phase=phase or "",
                updated_at=now,
                meta=meta or {},
            )
            with self.connect() as conn:
                conn.execute(
                    """
                    INSERT INTO task
                      (id, title, description, status, progress, sort_order, phase, updated_at, meta_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        t.id, t.title, t.description, t.status, t.progress,
                        t.sort_order, t.phase, t.updated_at, json.dumps(t.meta),
                    ),
                )
            return t

        new_title = title if title is not None else existing.title
        new_desc = description if description is not None else existing.description
        new_status = status if status is not None else existing.status
        new_progress = float(progress) if progress is not None else existing.progress
        new_phase = phase if phase is not None else existing.phase
        new_sort = int(sort_order) if sort_order is not None else existing.sort_order
        new_meta = {**(existing.meta or {}), **(meta or {})}
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE task SET title=?, description=?, status=?, progress=?,
                  sort_order=?, phase=?, updated_at=?, meta_json=?
                WHERE id=?
                """,
                (
                    new_title, new_desc, new_status, new_progress,
                    new_sort, new_phase, now, json.dumps(new_meta), task_id,
                ),
            )
        return self.get(task_id)  # type: ignore[return-value]

    def get(self, task_id: str) -> Task | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM task WHERE id=?", (task_id,)).fetchone()
        return self._row(row) if row else None

    def list(self) -> list[Task]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM task ORDER BY sort_order ASC, id ASC").fetchall()
        return [self._row(r) for r in rows]

    def start(self, task_id: str, note: str | None = None) -> Task:
        meta = {"last_note": note} if note else None
        cur = self.get(task_id)
        prog = max(cur.progress if cur else 0.0, 0.05)
        return self.upsert(task_id, status="in_progress", progress=prog, meta=meta)

    def complete(self, task_id: str, note: str | None = None) -> Task:
        meta = {"last_note": note} if note else None
        return self.upsert(task_id, status="completed", progress=1.0, meta=meta)

    def fail(self, task_id: str, error: str) -> Task:
        return self.upsert(task_id, status="failed", meta={"error": error})

    def set_progress(self, task_id: str, progress: float, note: str | None = None) -> Task:
        progress = max(0.0, min(1.0, float(progress)))
        status: Status = "completed" if progress >= 1.0 else "in_progress"
        meta = {"last_note": note} if note else None
        return self.upsert(task_id, status=status, progress=progress, meta=meta)

    @contextmanager
    def track(self, task_id: str, note: str | None = None) -> Iterator[TaskObserver]:
        """Mark in_progress on enter; completed on clean exit; failed on exception."""
        self.start(task_id, note=note)
        try:
            yield self
            self.complete(task_id, note=note)
        except Exception as e:  # noqa: BLE001
            self.fail(task_id, str(e))
            raise

    def refresh_from_world(self) -> dict[str, Any]:
        """Recompute status from api_call ledger + outputs so the board self-updates globally."""
        changes: list[str] = []
        with self.connect() as conn:
            # Ensure schema exists for older DBs that only had api_call
            conn.executescript(TASK_SCHEMA)
            phase_stats = {
                r["phase"]: dict(r)
                for r in conn.execute(
                    """
                    SELECT phase,
                           COUNT(*) AS calls,
                           COALESCE(SUM(CASE WHEN ok=1 THEN 1 ELSE 0 END),0) AS ok_calls,
                           COALESCE(SUM(cost_usd),0) AS cost_usd
                    FROM api_call
                    WHERE phase IS NOT NULL AND phase != ''
                      AND provider != 'demo'
                    GROUP BY phase
                    """
                ).fetchall()
            }

        # Dashboard is live if DB file exists (this process means it's usable)
        if self.path.exists():
            t = self.get("dashboard")
            if t and t.status != "completed":
                self.complete("dashboard", note="usage.db + TaskObserver active")
                changes.append("dashboard->completed")

        # Phase 0: need successful hellos from anthropic + openai + google
        with self.connect() as conn:
            providers_ok = {
                (r["provider"].split(":")[-1] if r["provider"] else "")
                for r in conn.execute(
                    """
                    SELECT DISTINCT provider FROM api_call
                    WHERE phase='phase0' AND ok=1 AND provider != 'demo'
                    """
                ).fetchall()
            }
        needed = {"anthropic", "openai", "google"}
        if needed.issubset(providers_ok):
            self.complete("phase0", note="anthropic/openai/google ok")
            changes.append("phase0->completed")
        elif providers_ok:
            missing = ", ".join(sorted(needed - providers_ok))
            self.start("phase0", note=f"waiting on: {missing}")
            changes.append("phase0->in_progress")
        else:
            # leave pending unless already failed by a script
            pass

        # Phase 1: image file or tracked image call
        p1_img = OUTPUTS / "phase1" / "nano_banana_hello.png"
        p1 = phase_stats.get("phase1")
        if p1_img.exists() or (p1 and p1["ok_calls"] > 0):
            self.complete("phase1", note=str(p1_img) if p1_img.exists() else "api ok")
            changes.append("phase1->completed")
        elif p1:
            self.start("phase1")
            changes.append("phase1->in_progress")

        # Phase 2: style_anchor or style grid
        anchor = OUTPUTS / "phase2" / "style_anchor.png"
        styles = list((OUTPUTS / "phase2").glob("style_*.png")) if (OUTPUTS / "phase2").exists() else []
        p2 = phase_stats.get("phase2")
        if anchor.exists() or len(styles) >= 3:
            self.complete("phase2", note=f"{len(styles)} style images")
            changes.append("phase2->completed")
        elif styles or p2:
            prog = min(0.9, len(styles) / 3.0) if styles else 0.1
            self.set_progress("phase2", prog, note=f"{len(styles)}/3 samples")
            changes.append(f"phase2->{prog:.0%}")

        # Mark any later phase with calls as at least in_progress
        for phase, stats in phase_stats.items():
            if phase in {"phase0", "phase1", "phase2", "dashboard"}:
                continue
            task = self.get(phase)
            if task and task.status == "pending" and stats["calls"] > 0:
                self.start(phase, note=f"{stats['calls']} calls")
                changes.append(f"{phase}->in_progress")

        # Romance stepper: infer from artifacts
        himym = OUTPUTS / "phase4" / "episode_how_i_met_your_mother_ep1.json"
        if himym.is_file():
            t1 = self.get("phase_romance_step1")
            if t1 and t1.status != "completed":
                self.complete("phase_romance_step1", note="episode JSON present")
                changes.append("phase_romance_step1->completed")

        refs_dir = OUTPUTS / "phase5" / "refs"
        # Require HIMYM-unique cast (not just shared dad/daughter from other stories)
        romance_must = ["rohan", "elena", "kabir", "arjun", "wei", "marcus"]
        romance_ref_hits = sum(
            1 for cid in romance_must if (refs_dir / f"{cid}_ref.png").is_file()
        )
        if romance_ref_hits >= 4:
            t2 = self.get("phase_romance_step2")
            if t2 and t2.status != "completed":
                self.complete("phase_romance_step2", note=f"{romance_ref_hits}/6 HIMYM refs")
                changes.append("phase_romance_step2->completed")
            elif t2 and t2.status == "pending":
                self.set_progress(
                    "phase_romance_step2",
                    romance_ref_hits / 6.0,
                    note=f"{romance_ref_hits}/6 HIMYM refs",
                )

        himym_panels = OUTPUTS / "phase5" / "episode_how_i_met_your_mother_ep1"
        if himym_panels.is_dir():
            pngs = list(himym_panels.glob("panel_*.png"))
            t3 = self.get("phase_romance_step3")
            target = 76
            if himym.is_file():
                try:
                    target = max(1, len(json.loads(himym.read_text()).get("panels") or []))
                except (OSError, json.JSONDecodeError, TypeError, ValueError):
                    target = 76
            if t3 and pngs:
                prog = min(0.99, len(pngs) / float(target))
                if len(pngs) >= target and (t3.status != "completed"):
                    man = himym_panels / "manifest.json"
                    err = 0
                    if man.is_file():
                        try:
                            err = int(json.loads(man.read_text()).get("errors") or 0)
                        except (OSError, json.JSONDecodeError, TypeError, ValueError):
                            err = 0
                    if err == 0:
                        self.complete("phase_romance_step3", note=f"{len(pngs)} panels")
                        changes.append("phase_romance_step3->completed")
                    else:
                        self.set_progress("phase_romance_step3", prog, note=f"{len(pngs)} panels · errors={err}")
                elif t3.status != "completed":
                    self.set_progress("phase_romance_step3", max(prog, 0.05), note=f"{len(pngs)}/{target} panels")
                    changes.append(f"phase_romance_step3->{prog:.0%}")

        return {"changes": changes, "phase_stats": phase_stats}

    def romance_snapshot(self) -> dict[str, Any]:
        """Stepper payload for How I Met Your Mother romance pipeline."""
        ids = [
            "phase_romance_step1",
            "phase_romance_step2",
            "phase_romance_step3",
            "phase_romance_step4",
            "phase_romance_step5",
        ]
        steps = []
        for tid in ids:
            t = self.get(tid)
            if t:
                steps.append(t.as_dict())
            else:
                steps.append(
                    {
                        "id": tid,
                        "title": tid,
                        "status": "pending",
                        "progress": 0.0,
                        "description": "",
                        "meta": {},
                    }
                )
        done = sum(1 for s in steps if s.get("status") == "completed")
        # Soft credit for partial progress on current step
        partial = 0.0
        for s in steps:
            if s.get("status") == "in_progress":
                partial = float(s.get("progress") or 0) * 0.2
                break
        spend = 0.0
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(cost_usd),0) AS cost_usd
                FROM api_call
                WHERE phase LIKE 'phase_romance%' AND provider != 'demo'
                """
            ).fetchone()
            if row:
                spend = float(row["cost_usd"] or 0)
        return {
            "steps": steps,
            "completion_ratio": min(1.0, (done + partial) / max(len(steps), 1)),
            "completed": done,
            "total": len(steps),
            "spend_usd": spend,
            "label": "How I Met Your Mother",
        }

    def snapshot(self) -> dict[str, Any]:
        # Self-heal / auto-update before every read
        refresh = self.refresh_from_world()
        tasks = [t.as_dict() for t in self.list()]
        counts = {"pending": 0, "in_progress": 0, "completed": 0, "failed": 0, "blocked": 0}
        for t in tasks:
            counts[t["status"]] = counts.get(t["status"], 0) + 1
        done = counts["completed"]
        total = len(tasks) or 1
        return {
            "tasks": tasks,
            "counts": counts,
            "completion_ratio": done / total,
            "romance": self.romance_snapshot(),
            "refresh": refresh,
            "updated_at": _utcnow(),
        }

    @staticmethod
    def _row(row: sqlite3.Row) -> Task:
        meta_raw = row["meta_json"] or "{}"
        try:
            meta = json.loads(meta_raw)
        except json.JSONDecodeError:
            meta = {}
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"] or "",
            status=row["status"],
            progress=float(row["progress"] or 0),
            sort_order=int(row["sort_order"] or 0),
            phase=row["phase"] or "",
            updated_at=row["updated_at"] or "",
            meta=meta,
        )


# Module singleton — all scripts share one observer pointing at global DB
observer = TaskObserver()
