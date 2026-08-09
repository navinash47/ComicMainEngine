#!/usr/bin/env python3
"""CLI for the global TaskObserver board."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.tasks import observer


def main() -> None:
    p = argparse.ArgumentParser(description="ComicEngine TaskObserver")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="Show global tasks (auto-refreshes from world)")
    sub.add_parser("refresh", help="Force refresh from api_call + outputs")

    s = sub.add_parser("start", help="Mark task in_progress")
    s.add_argument("id")
    s.add_argument("--note", default=None)

    c = sub.add_parser("done", help="Mark task completed")
    c.add_argument("id")
    c.add_argument("--note", default=None)

    f = sub.add_parser("fail", help="Mark task failed")
    f.add_argument("id")
    f.add_argument("error")

    pr = sub.add_parser("progress", help="Set 0..1 progress")
    pr.add_argument("id")
    pr.add_argument("value", type=float)
    pr.add_argument("--note", default=None)

    args = p.parse_args()

    if args.cmd == "list":
        print(json.dumps(observer.snapshot(), indent=2))
    elif args.cmd == "refresh":
        print(json.dumps(observer.snapshot(), indent=2))
    elif args.cmd == "start":
        print(json.dumps(observer.start(args.id, note=args.note).as_dict(), indent=2))
    elif args.cmd == "done":
        print(json.dumps(observer.complete(args.id, note=args.note).as_dict(), indent=2))
    elif args.cmd == "fail":
        print(json.dumps(observer.fail(args.id, args.error).as_dict(), indent=2))
    elif args.cmd == "progress":
        print(json.dumps(observer.set_progress(args.id, args.value, note=args.note).as_dict(), indent=2))


if __name__ == "__main__":
    main()
