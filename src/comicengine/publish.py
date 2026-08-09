"""Phase 10 — export approved Library editions for Cloudflare Pages + R2."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from comicengine.config import (
    BETA_PUBLISH_APPROVED_ONLY,
    CF_ACCOUNT_ID,
    CF_PAGES_PROJECT,
    CF_R2_ACCESS_KEY_ID,
    CF_R2_BUCKET,
    CF_R2_SECRET_ACCESS_KEY,
    OUTPUTS,
    ROOT,
)
from comicengine.library import load_catalog, rebuild_catalog

PHASE10 = OUTPUTS / "phase10"
SITE_DIR = PHASE10 / "site"
MANIFEST_PATH = PHASE10 / "publish_manifest.json"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _copy_if_exists(src: Path, dest: Path) -> bool:
    if not src.is_file():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return True


def selected_stories(catalog: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    cat = catalog or load_catalog(refresh=False)
    stories = cat.get("stories") or []
    if not BETA_PUBLISH_APPROVED_ONLY:
        return list(stories)
    out = []
    for s in stories:
        cur = s.get("curation") or {}
        if (cur.get("episode_status") or "pending") == "approved":
            out.append(s)
    # Soft fallback so beta isn't empty before curation completes
    if not out and stories:
        return list(stories)
    return out


def export_beta_site(*, refresh_catalog: bool = True) -> dict[str, Any]:
    """Build static beta package under outputs/phase10/site."""
    catalog = rebuild_catalog() if refresh_catalog else load_catalog(refresh=False)
    stories = selected_stories(catalog)
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    media_dir = SITE_DIR / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    # Copy dashboard static reader shell pieces
    static_src = ROOT / "dashboard" / "static"
    for name in (
        "styles.css",
        "library.html",
        "library.js",
        "story.html",
        "story.js",
        "feedback.html",
        "feedback.js",
        "auth.js",
        "curation_editor.js",
    ):
        src = static_src / name
        if src.is_file():
            shutil.copy2(src, SITE_DIR / name)

    exported: list[dict[str, Any]] = []
    for story in stories:
        sid = story["id"]
        entry: dict[str, Any] = {"id": sid, "title": story.get("title"), "files": []}
        eds = story.get("editions") or {}
        for key, ed in eds.items():
            for href_key in ("webtoon_href", "pdf_href"):
                href = (ed or {}).get(href_key) or ""
                if not href.startswith("/media/"):
                    continue
                rel = href[len("/media/") :]
                src = OUTPUTS / rel
                dest = media_dir / rel
                if _copy_if_exists(src, dest):
                    entry["files"].append({"edition": key, "path": f"media/{rel}"})
        # episode JSON if discoverable
        for cand in (
            OUTPUTS / "phase0.5" / f"{sid}.json",
            OUTPUTS / "phase4" / f"{sid}.json",
        ):
            if cand.is_file():
                dest = SITE_DIR / "episodes" / cand.name
                _copy_if_exists(cand, dest)
                entry["files"].append({"edition": "json", "path": f"episodes/{cand.name}"})
                break
        exported.append(entry)

    index = SITE_DIR / "index.html"
    index.write_text(
        """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ComicEngine Beta</title>
  <link rel="stylesheet" href="./styles.css" />
  <meta http-equiv="refresh" content="0; url=./library.html" />
</head>
<body>
  <p style="padding:2rem">Opening <a href="./library.html">Story Library</a>…</p>
</body>
</html>
""",
        encoding="utf-8",
    )

    (SITE_DIR / "catalog.json").write_text(
        json.dumps({"updated_at": _utcnow(), "stories": stories, "beta": True}, indent=2),
        encoding="utf-8",
    )

    manifest = {
        "phase": "phase10",
        "exported_at": _utcnow(),
        "approved_only": BETA_PUBLISH_APPROVED_ONLY,
        "story_count": len(exported),
        "stories": exported,
        "site_dir": str(SITE_DIR.relative_to(ROOT)),
        "cloudflare": {
            "account_id_set": bool(CF_ACCOUNT_ID),
            "r2_bucket": CF_R2_BUCKET,
            "pages_project": CF_PAGES_PROJECT,
            "r2_creds_set": bool(CF_R2_ACCESS_KEY_ID and CF_R2_SECRET_ACCESS_KEY),
        },
        "notes": (
            "Static mirror for Pages/R2. Live Google login + Mom Test feedback "
            "require the FastAPI app (tunnel or host) — see docs/BETA_SETUP.md."
        ),
    }
    PHASE10.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    try:
        from comicengine.usage import UsageDB

        UsageDB().log_local(
            phase="phase10",
            purpose="export_beta_site",
            note=f"exported {len(exported)} stories",
            meta={"story_count": len(exported)},
        )
    except Exception:  # noqa: BLE001
        pass
    return manifest


def upload_site_to_r2() -> dict[str, Any]:
    """Upload outputs/phase10/site to R2 via boto3 (optional dependency)."""
    if not (CF_ACCOUNT_ID and CF_R2_ACCESS_KEY_ID and CF_R2_SECRET_ACCESS_KEY):
        raise RuntimeError(
            "Set CF_ACCOUNT_ID, CF_R2_ACCESS_KEY_ID, CF_R2_SECRET_ACCESS_KEY in .env"
        )
    if not SITE_DIR.is_dir():
        export_beta_site()

    try:
        import boto3
        from botocore.config import Config
    except ImportError as e:
        raise RuntimeError("Install boto3 for R2 upload: pip install boto3") from e

    endpoint = f"https://{CF_ACCOUNT_ID}.r2.cloudflarestorage.com"
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=CF_R2_ACCESS_KEY_ID,
        aws_secret_access_key=CF_R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )
    uploaded = 0
    for path in SITE_DIR.rglob("*"):
        if not path.is_file():
            continue
        key = path.relative_to(SITE_DIR).as_posix()
        extra = {}
        if path.suffix == ".html":
            extra["ContentType"] = "text/html; charset=utf-8"
        elif path.suffix == ".js":
            extra["ContentType"] = "application/javascript; charset=utf-8"
        elif path.suffix == ".css":
            extra["ContentType"] = "text/css; charset=utf-8"
        elif path.suffix == ".json":
            extra["ContentType"] = "application/json"
        elif path.suffix == ".pdf":
            extra["ContentType"] = "application/pdf"
        elif path.suffix == ".png":
            extra["ContentType"] = "image/png"
        client.upload_file(str(path), CF_R2_BUCKET, key, ExtraArgs=extra or None)
        uploaded += 1
    return {
        "ok": True,
        "bucket": CF_R2_BUCKET,
        "uploaded": uploaded,
        "endpoint": endpoint,
    }
