#!/usr/bin/env python3
"""Phase 8.6 — Mom Test feedback + reviewer ledger helpers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.feedback import feedback
from comicengine.reviewers import reviewers
from comicengine.tasks import observer


def main() -> None:
    p = argparse.ArgumentParser(description="Phase 8.6 feedback / reviewers")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("gate", help="Mark phase 8.6 complete")
    sub.add_parser("questions", help="Print Mom Test questionnaire JSON")
    sub.add_parser("summary", help="Feedback + reviewer counts")
    sub.add_parser("export", help="Export feedback dump for Version 2")
    pe = sub.add_parser("export-file", help="Write export JSON under outputs/phase8.6/")
    pe.add_argument("--out", default=str(ROOT / "outputs" / "phase8.6" / "feedback_export.json"))

    args = p.parse_args()
    if args.cmd == "gate":
        observer.upsert(
            "phase8.6",
            title="Phase 8.6 — Google auth + Mom Test feedback",
            description="Google login, reviewer ledger, Mom Test questionnaire, admin feedback log",
            phase="phase8.6",
            sort_order=86,
            status="in_progress",
            progress=0.5,
        )
        observer.complete(
            "phase8.6",
            note="auth + Mom Test questionnaire + reviewer/feedback SQLite logs",
        )
        print(json.dumps({"ok": True, "phase": "phase8.6", **feedback.summary()}, indent=2))
    elif args.cmd == "questions":
        print(json.dumps(feedback.questionnaire_meta(), indent=2))
    elif args.cmd == "summary":
        print(json.dumps({"reviewers": reviewers.summary(), "feedback": feedback.summary()}, indent=2))
    elif args.cmd == "export":
        print(json.dumps(feedback.export_for_future(), indent=2))
    elif args.cmd == "export-file":
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(feedback.export_for_future(), indent=2), encoding="utf-8")
        print(json.dumps({"ok": True, "path": str(out)}, indent=2))


if __name__ == "__main__":
    main()
