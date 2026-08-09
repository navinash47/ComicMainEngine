#!/usr/bin/env python3
"""Phase 8.5 — panel human rating, suggestions, editable regen prompts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.curation import curation, panel_editor_payload, regenerate_panel
from comicengine.library import rebuild_catalog
from comicengine.tasks import observer


def main() -> None:
    p = argparse.ArgumentParser(description="Phase 8.5 panel editor / rating CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("gate", help="Mark phase 8.5 complete after UI land")

    pe = sub.add_parser("editor", help="Dump panel editor payload (prompt + rating)")
    pe.add_argument("story_id")
    pe.add_argument("--panel", type=int, required=True)

    pr = sub.add_parser("rate", help="Set rating + suggestions (+ optional status)")
    pr.add_argument("story_id")
    pr.add_argument("--panel", type=int, required=True)
    pr.add_argument("--rating", type=int, required=True)
    pr.add_argument("--suggestions", default="")
    pr.add_argument("--status", default=None)
    pr.add_argument("--note", default="")

    rg = sub.add_parser("regenerate", help="Regen with optional edited prompt")
    rg.add_argument("story_id")
    rg.add_argument("--panel", type=int, required=True)
    rg.add_argument("--prompt", default=None)
    rg.add_argument("--rating", type=int, default=None)
    rg.add_argument("--suggestions", default=None)
    rg.add_argument("--note", default="")
    rg.add_argument("--reject-first", action="store_true")

    args = p.parse_args()

    try:
        if args.cmd == "gate":
            observer.upsert(
                "phase8.5",
                title="Phase 8.5 — Panel rating + prompt editor",
                description="Rate/suggest panels; edit prompts on reject/regen; live site refresh",
                phase="phase8.5",
                sort_order=85,
                status="in_progress",
                progress=0.5,
            )
            rebuild_catalog()
            observer.complete(
                "phase8.5",
                note="rating + suggestions + editable regen prompt on Library/Story",
            )
            print(json.dumps({"ok": True, "phase": "phase8.5"}, indent=2))
        elif args.cmd == "editor":
            print(json.dumps(panel_editor_payload(args.story_id, args.panel), indent=2))
        elif args.cmd == "rate":
            item = curation.upsert(
                story_id=args.story_id,
                panel_index=args.panel,
                status=args.status,  # type: ignore[arg-type]
                note=args.note or "rated via CLI",
                rating=args.rating,
                suggestions=args.suggestions,
            )
            print(json.dumps(item, indent=2))
        elif args.cmd == "regenerate":
            result = regenerate_panel(
                args.story_id,
                args.panel,
                note=args.note,
                prompt=args.prompt,
                rating=args.rating,
                suggestions=args.suggestions,
                mark_rejected_first=args.reject_first,
            )
            print(
                json.dumps(
                    {
                        "ok": True,
                        "item": result["item"],
                        "method": result["render"].get("method"),
                        "image_href": result.get("image_href"),
                    },
                    indent=2,
                )
            )
    except Exception as e:  # noqa: BLE001
        if args.cmd == "gate":
            observer.fail("phase8.5", str(e))
        raise


if __name__ == "__main__":
    main()
