#!/usr/bin/env python3
"""Phase 8 — curation CLI: list / approve / reject / regenerate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.curation import curation, regenerate_panel
from comicengine.library import rebuild_catalog
from comicengine.tasks import observer


def _print_items(items: list[dict]) -> None:
    if not items:
        print("(none)")
        return
    for it in items:
        loc = (
            f"panel {it['panel_index']}"
            if it.get("kind") == "panel"
            else "episode"
        )
        note = (it.get("note") or "")[:60]
        print(
            f"{it['status']:12}  {it['story_id']:28}  {loc:10}  "
            f"r={it.get('rating') or '-'}  {note}"
        )


def main() -> None:
    p = argparse.ArgumentParser(description="Phase 8 curation CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("seed", help="Seed pending rows for all episode panels")
    sub.add_parser("summary", help="Curation counts by status/story")

    pl = sub.add_parser("list", help="List curation items")
    pl.add_argument("--story", default=None)
    pl.add_argument("--status", default=None)
    pl.add_argument("--kind", choices=["episode", "panel"], default=None)

    for name in ("approve", "reject"):
        px = sub.add_parser(name, help=f"{name} episode or panel")
        px.add_argument("story_id")
        px.add_argument("--panel", type=int, default=None)
        px.add_argument("--note", default="")

    pr = sub.add_parser("regenerate", help="Re-render + recompose one panel")
    pr.add_argument("story_id")
    pr.add_argument("--panel", type=int, required=True)
    pr.add_argument("--note", default="")
    pr.add_argument("--prompt", default=None)
    pr.add_argument("--rating", type=int, default=None)
    pr.add_argument("--suggestions", default=None)

    args = p.parse_args()

    try:
        if args.cmd == "seed":
            observer.upsert(
                "phase8",
                title="Phase 8 — Curation CLI + SQLite",
                description="Approve / reject / regenerate panels & episodes",
                phase="phase8",
                sort_order=80,
                status="in_progress",
                progress=0.3,
            )
            out = curation.seed_from_stories()
            rebuild_catalog()
            observer.complete("phase8", note=f"seeded {out['created']} rows")
            print(json.dumps(out, indent=2))
        elif args.cmd == "summary":
            print(json.dumps(curation.summary(), indent=2))
        elif args.cmd == "list":
            items = curation.list(story_id=args.story, status=args.status, kind=args.kind)
            _print_items(items)
        elif args.cmd in {"approve", "reject"}:
            status = "approved" if args.cmd == "approve" else "rejected"
            item = curation.upsert(
                story_id=args.story_id,
                panel_index=args.panel,
                status=status,
                note=args.note or status,
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
        if args.cmd == "seed":
            observer.fail("phase8", str(e))
        raise


if __name__ == "__main__":
    main()
