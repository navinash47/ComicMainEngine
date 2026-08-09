"""Phase 8.6 — beta feedback questionnaire + durable response log."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Literal

from comicengine.config import USAGE_DB_PATH

QuestionKind = Literal["rating", "text", "choice", "nps"]

# Mom Test (Rob Fitzpatrick): ask about their life + specific past behavior,
# not compliments, hypotheticals, or “would you use/pay/recommend?”.
FEEDBACK_INTRO = (
    "Please answer from real past moments — what you and kids / students "
    "actually do — and what happened while you read today. Skip flattery; "
    "concrete details help Version 2 a lot more than ratings alone."
)

FEEDBACK_QUESTIONS: list[dict[str, Any]] = [
    # --- Their world (before pitching the product) ---
    {
        "id": "q01_role_context",
        "kind": "choice",
        "required": True,
        "section": "Your world",
        "prompt": "In the last month, which role were you actually in when history or bedtime stories came up?",
        "choices": [
            "parent / guardian at home",
            "teacher / tutor with students",
            "older sibling / relative",
            "student learning history myself",
            "none — I don’t do this regularly",
            "other",
        ],
    },
    {
        "id": "q02_last_time",
        "kind": "text",
        "required": True,
        "section": "Your world",
        "prompt": "Tell me about the last time you tried to explain a hard history topic to a kid or learner.",
        "hint": "When was it, who was there, what topic, what did you use (YouTube, book, chat…)?",
    },
    {
        "id": "q03_what_broke",
        "kind": "text",
        "required": True,
        "section": "Your world",
        "prompt": "In that attempt (or a similar recent one), what went wrong or felt hardest?",
        "hint": "Attention dropped? Too scary? You didn’t know enough? No good material?",
    },
    {
        "id": "q04_current_tools",
        "kind": "text",
        "required": True,
        "section": "Your world",
        "prompt": "What do you already use today for history / morals / bedtime explainers?",
        "hint": "Names of apps, channels, books, comics — or “nothing reliable.”",
    },
    {
        "id": "q05_sought_before",
        "kind": "choice",
        "required": True,
        "section": "Your world",
        "prompt": "Before today, had you searched for or paid for something like an illustrated history comic for kids/teens?",
        "choices": [
            "yes — paid for something",
            "yes — searched but didn’t buy",
            "yes — used free stuff only",
            "no — never looked",
            "not sure",
        ],
    },
    {
        "id": "q06_when_need",
        "kind": "choice",
        "required": True,
        "section": "Your world",
        "prompt": "When does this need usually show up in your week?",
        "choices": [
            "bedtime / wind-down",
            "homework / school project",
            "classroom period",
            "random curiosity moment",
            "rarely / never",
            "other",
        ],
    },
    # --- What they actually did in this beta session ---
    {
        "id": "q07_story_opened",
        "kind": "choice",
        "required": True,
        "section": "This session",
        "prompt": "Which story did you actually open first today?",
        "choices": [
            "episode_cjp_origin",
            "episode_et_tu_brutus",
            "episode_hitler_warning",
            "more than one",
            "I only skimmed the library",
        ],
    },
    {
        "id": "q08_how_far",
        "kind": "choice",
        "required": True,
        "section": "This session",
        "prompt": "How far did you get in that story before you stopped or switched away?",
        "choices": [
            "never started reading panels",
            "stopped in the first few panels",
            "about halfway",
            "finished (or almost finished)",
            "finished more than one story",
        ],
    },
    {
        "id": "q09_minutes",
        "kind": "choice",
        "required": True,
        "section": "This session",
        "prompt": "About how many minutes did you spend reading (not including chatting with us)?",
        "choices": ["under 3", "3–10", "10–20", "20–40", "over 40"],
    },
    {
        "id": "q10_first_stop",
        "kind": "text",
        "required": True,
        "section": "This session",
        "prompt": "Where did you first stop, skim, or feel the urge to leave? What was on screen?",
        "hint": "Panel number/scene if you remember — “don’t remember stopping” is fine.",
    },
    {
        "id": "q11_reread",
        "kind": "text",
        "required": True,
        "section": "This session",
        "prompt": "Did you re-read any bubble or caption because it was unclear? Quote or paraphrase it.",
        "hint": "If none, write “none.”",
    },
    {
        "id": "q12_visual_break",
        "kind": "text",
        "required": True,
        "section": "This session",
        "prompt": "Name one visual moment that broke immersion (face swap, weird hands, unreadably small text, blank look…).",
        "hint": "If nothing broke it, write “nothing broke immersion.”",
    },
    {
        "id": "q13_flinch",
        "kind": "text",
        "required": True,
        "section": "This session",
        "prompt": "Was there a moment you flinched for a child’s sake — too intense, confusing, or off-tone? Describe it.",
        "hint": "If no flinch, write “no flinch.”",
    },
    {
        "id": "q14_learned_or_stuck",
        "kind": "text",
        "required": True,
        "section": "This session",
        "prompt": "After reading, what could you retell in one sentence — and what are you still unsure about?",
    },
    {
        "id": "q15_showed_anyone",
        "kind": "choice",
        "required": True,
        "section": "Commitment signals",
        "prompt": "Since opening this beta, have you already shown a panel or mentioned it to anyone else?",
        "choices": [
            "yes — showed a screen to someone",
            "yes — told someone about it (no screen)",
            "not yet, but I know who I’d show",
            "no",
        ],
    },
    {
        "id": "q16_who_and_what",
        "kind": "text",
        "required": False,
        "section": "Commitment signals",
        "prompt": "If yes (or if you know who you’d show), who — and what did you / would you say was the point?",
    },
    {
        "id": "q17_compared_to",
        "kind": "text",
        "required": True,
        "section": "Commitment signals",
        "prompt": "Compared to the last tool you used for this job, what did this comic do better or worse in practice today?",
        "hint": "Talk about what happened, not what might happen later.",
    },
    {
        "id": "q18_still_missing",
        "kind": "text",
        "required": True,
        "section": "Commitment signals",
        "prompt": "What job is still unfinished for you after reading? (e.g. kid still bored, I still can’t answer a question, need audio…)",
    },
    {
        "id": "q19_device",
        "kind": "choice",
        "required": True,
        "section": "Context",
        "prompt": "What device did you use for most of this session?",
        "choices": ["phone", "tablet", "laptop / desktop", "mixed"],
    },
    {
        "id": "q20_open",
        "kind": "text",
        "required": False,
        "section": "Context",
        "prompt": "Anything else that happened while reading that we didn’t ask about?",
        "hint": "Facts and moments beat opinions. Skip “looks great!” unless you can point at a panel.",
    },
]

FEEDBACK_SCHEMA = """
CREATE TABLE IF NOT EXISTS feedback_response (
  id TEXT PRIMARY KEY,
  reviewer_id TEXT NOT NULL,
  reviewer_email TEXT NOT NULL,
  reviewer_name TEXT DEFAULT '',
  story_id TEXT DEFAULT '',
  created_at TEXT NOT NULL,
  overall_rating REAL,
  nps INTEGER,
  answers_json TEXT NOT NULL,
  suggestions TEXT DEFAULT '',
  user_agent TEXT DEFAULT '',
  meta_json TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_feedback_reviewer ON feedback_response(reviewer_id);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback_response(created_at);
CREATE INDEX IF NOT EXISTS idx_feedback_story ON feedback_response(story_id);
"""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class FeedbackDB:
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
            conn.executescript(FEEDBACK_SCHEMA)

    def questions(self) -> list[dict[str, Any]]:
        return list(FEEDBACK_QUESTIONS)

    def questionnaire_meta(self) -> dict[str, Any]:
        return {
            "method": "mom_test",
            "intro": FEEDBACK_INTRO,
            "question_count": len(FEEDBACK_QUESTIONS),
            "questions": self.questions(),
        }

    def submit(
        self,
        *,
        reviewer: dict[str, Any],
        answers: dict[str, Any],
        story_id: str = "",
        user_agent: str = "",
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        cleaned, errors = self.validate_answers(answers)
        if errors:
            raise ValueError("; ".join(errors))

        overall = self._completion_score(cleaned)
        commit = self._commitment_score(cleaned)
        text_ids = [
            "q02_last_time",
            "q03_what_broke",
            "q04_current_tools",
            "q10_first_stop",
            "q11_reread",
            "q12_visual_break",
            "q13_flinch",
            "q14_learned_or_stuck",
            "q16_who_and_what",
            "q17_compared_to",
            "q18_still_missing",
            "q20_open",
        ]
        suggestions_parts = [
            f"{qid}: {str(cleaned.get(qid) or '').strip()}"
            for qid in text_ids
            if cleaned.get(qid)
        ]
        rid = str(uuid.uuid4())
        now = _utcnow()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO feedback_response(
                  id, reviewer_id, reviewer_email, reviewer_name, story_id,
                  created_at, overall_rating, nps, answers_json, suggestions,
                  user_agent, meta_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    rid,
                    reviewer.get("id") or "",
                    reviewer.get("email") or "",
                    reviewer.get("name") or "",
                    story_id or str(cleaned.get("q07_story_opened") or ""),
                    now,
                    overall,
                    commit,
                    json.dumps(cleaned, ensure_ascii=False),
                    "\n\n".join(suggestions_parts),
                    user_agent[:500],
                    json.dumps(
                        {
                            **(meta or {}),
                            "method": "mom_test",
                            "intro": FEEDBACK_INTRO,
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
        return self.get(rid) or {}

    def validate_answers(self, answers: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        out: dict[str, Any] = {}
        errors: list[str] = []
        by_id = {q["id"]: q for q in FEEDBACK_QUESTIONS}
        for q in FEEDBACK_QUESTIONS:
            qid = q["id"]
            raw = answers.get(qid)
            if raw is None or (isinstance(raw, str) and not raw.strip()):
                if q.get("required"):
                    errors.append(f"{qid} is required")
                continue
            kind = q["kind"]
            if kind in {"rating", "nps"}:
                try:
                    n = int(raw)
                except (TypeError, ValueError):
                    errors.append(f"{qid} must be a number")
                    continue
                lo = int(q.get("min", 1 if kind == "rating" else 0))
                hi = int(q.get("max", 5 if kind == "rating" else 10))
                if not (lo <= n <= hi):
                    errors.append(f"{qid} must be {lo}–{hi}")
                    continue
                out[qid] = n
            elif kind == "choice":
                val = str(raw).strip()
                choices = q.get("choices") or []
                if choices and val not in choices:
                    errors.append(f"{qid} invalid choice")
                    continue
                out[qid] = val
            else:
                out[qid] = str(raw).strip()
        # ignore unknown keys silently but keep extras under _extra
        extra = {k: v for k, v in answers.items() if k not in by_id}
        if extra:
            out["_extra"] = extra
        return out, errors

    def get(self, response_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM feedback_response WHERE id=?", (response_id,)
            ).fetchone()
        return self._row(row) if row else None

    def list(
        self,
        *,
        reviewer_id: str | None = None,
        story_id: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM feedback_response WHERE 1=1"
        args: list[Any] = []
        if reviewer_id:
            sql += " AND reviewer_id=?"
            args.append(reviewer_id)
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
            total = conn.execute("SELECT COUNT(*) AS n FROM feedback_response").fetchone()["n"]
            avg = conn.execute(
                "SELECT AVG(overall_rating) AS a FROM feedback_response WHERE overall_rating IS NOT NULL"
            ).fetchone()["a"]
            nps_avg = conn.execute(
                "SELECT AVG(nps) AS a FROM feedback_response WHERE nps IS NOT NULL"
            ).fetchone()["a"]
            by_story = [
                dict(r)
                for r in conn.execute(
                    """
                    SELECT story_id, COUNT(*) AS n, AVG(overall_rating) AS avg_rating
                    FROM feedback_response
                    GROUP BY story_id
                    ORDER BY n DESC
                    """
                ).fetchall()
            ]
        return {
            "responses": total,
            "avg_completion_score": round(float(avg), 2) if avg is not None else None,
            "avg_overall_rating": round(float(avg), 2) if avg is not None else None,
            "avg_commitment_score": round(float(nps_avg), 2) if nps_avg is not None else None,
            "avg_nps": round(float(nps_avg), 2) if nps_avg is not None else None,
            "by_story": by_story,
            "question_count": len(FEEDBACK_QUESTIONS),
            "method": "mom_test",
        }

    def export_for_future(self) -> dict[str, Any]:
        """Structured dump for Version 2 / Phase 12+ planning."""
        return {
            "exported_at": _utcnow(),
            "method": "mom_test",
            "intro": FEEDBACK_INTRO,
            "questions": self.questions(),
            "summary": self.summary(),
            "responses": self.list(limit=5000),
        }

    @staticmethod
    def _completion_score(answers: dict[str, Any]) -> float | None:
        """Map how far they got to a 1–5 depth score (behavior, not vanity)."""
        mapping = {
            "never started reading panels": 1.0,
            "stopped in the first few panels": 2.0,
            "about halfway": 3.0,
            "finished (or almost finished)": 4.5,
            "finished more than one story": 5.0,
        }
        how_far = answers.get("q08_how_far")
        if how_far in mapping:
            return mapping[how_far]
        return None

    @staticmethod
    def _commitment_score(answers: dict[str, Any]) -> int | None:
        """0–10 scale from real sharing behavior (not hypothetical NPS)."""
        mapping = {
            "yes — showed a screen to someone": 10,
            "yes — told someone about it (no screen)": 7,
            "not yet, but I know who I’d show": 4,
            "no": 1,
        }
        shown = answers.get("q15_showed_anyone")
        if shown in mapping:
            return mapping[shown]
        return None

    @staticmethod
    def _mean_ratings(answers: dict[str, Any]) -> float | None:
        vals = [
            float(answers[q["id"]])
            for q in FEEDBACK_QUESTIONS
            if q["kind"] == "rating" and q["id"] in answers
        ]
        if not vals:
            return None
        return round(sum(vals) / len(vals), 3)

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        try:
            d["answers"] = json.loads(d.pop("answers_json") or "{}")
        except json.JSONDecodeError:
            d["answers"] = {}
        try:
            d["meta"] = json.loads(d.pop("meta_json") or "{}")
        except json.JSONDecodeError:
            d["meta"] = {}
        return d


feedback = FeedbackDB()
