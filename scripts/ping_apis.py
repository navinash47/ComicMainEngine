#!/usr/bin/env python3
"""Cheap API hello checks — logs tokens/cost. No images."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.clients import ping_all
from comicengine.tasks import observer


def main() -> None:
    observer.start("phase0", note="API hello pings")
    results = ping_all(phase="phase0")
    failed = [k for k, v in results.items() if not v.get("ok")]
    if failed:
        observer.fail("phase0", f"failed: {', '.join(failed)}")
    else:
        observer.complete("phase0", note="anthropic/openai/google ok")
    observer.refresh_from_world()
    print(json.dumps(results, indent=2))
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
