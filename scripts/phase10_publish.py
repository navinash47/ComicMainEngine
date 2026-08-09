#!/usr/bin/env python3
"""Phase 10 — export / upload beta package (Cloudflare Pages + R2)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.publish import SITE_DIR, export_beta_site, upload_site_to_r2
from comicengine.tasks import observer


def main() -> None:
    p = argparse.ArgumentParser(description="Phase 10 publish")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("export", help="Build outputs/phase10/site")
    sub.add_parser("upload-r2", help="Upload site tree to Cloudflare R2")
    sub.add_parser("deploy-pages", help="wrangler pages deploy (requires wrangler + login)")
    sub.add_parser("gate", help="Mark phase 10 after export succeeds")

    args = p.parse_args()
    try:
        if args.cmd == "export":
            out = export_beta_site(refresh_catalog=True)
            print(json.dumps(out, indent=2))
        elif args.cmd == "upload-r2":
            print(json.dumps(upload_site_to_r2(), indent=2))
        elif args.cmd == "deploy-pages":
            if not SITE_DIR.is_dir():
                export_beta_site()
            cmd = [
                "npx",
                "--yes",
                "wrangler",
                "pages",
                "deploy",
                str(SITE_DIR),
                "--project-name",
                "comicengine-beta",
            ]
            print("Running:", " ".join(cmd))
            subprocess.check_call(cmd, cwd=str(ROOT))
        elif args.cmd == "gate":
            observer.upsert(
                "phase10",
                title="Phase 10 — Publishing pipeline",
                description="Cloudflare Pages + R2 export of Library editions",
                phase="phase10",
                sort_order=100,
                status="in_progress",
                progress=0.4,
            )
            man = export_beta_site(refresh_catalog=True)
            observer.complete(
                "phase10",
                note=f"exported {man.get('story_count')} stories → {man.get('site_dir')}",
            )
            print(json.dumps({"ok": True, "manifest": man}, indent=2))
    except Exception as e:  # noqa: BLE001
        if args.cmd == "gate":
            observer.fail("phase10", str(e))
        raise


if __name__ == "__main__":
    main()
