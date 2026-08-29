#!/usr/bin/env python3
"""Download Kenney CC0 protagonists and bake seated/standing GLBs via Blender."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

from comicengine.v2b.blender.run_headless import blender_bin  # noqa: E402
from comicengine.config import ROOT as CE_ROOT  # noqa: E402

MESH_DIR = CE_ROOT / "data" / "v2b" / "meshes"
REGISTRY = MESH_DIR / "registry.json"
CACHE = MESH_DIR / "cache"
BAKE = CE_ROOT / "src" / "comicengine" / "v2b" / "blender" / "bake_kenney.py"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 1000:
        return dest
    print(f"download {url}", flush=True)
    urllib.request.urlretrieve(url, dest)
    return dest


def _extract(zip_path: Path, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    marker = dest / "Model" / "characterMedium.fbx"
    if marker.is_file():
        return dest
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest)
    return dest


def bake_one(extract: Path, character: str, pose: str, spec: dict, fbx: str) -> dict[str, object]:
    glb = MESH_DIR / spec[pose]
    if glb.is_file() and glb.stat().st_size > 1000:
        return {"character": character, "pose": pose, "glb": str(glb), "reused": True}
    cmd = [
        str(blender_bin()),
        "--background",
        "--factory-startup",
        "--python",
        str(BAKE),
        "--",
        "--extract",
        str(extract),
        "--out-dir",
        str(MESH_DIR),
        "--character",
        character,
        "--pose",
        pose,
        "--skin",
        str(spec["skin"]),
        "--fbx",
        fbx,
        "--target-height",
        str(spec["target_height"]),
    ]
    proc = subprocess.run(cmd, cwd=str(CE_ROOT), capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not glb.is_file():
        raise RuntimeError(
            "Kenney bake failed.\n"
            f"cmd: {cmd}\n"
            f"exit: {proc.returncode}\n"
            f"stdout:\n{proc.stdout[-3000:]}\n"
            f"stderr:\n{proc.stderr[-3000:]}"
        )
    return json.loads(glb.with_suffix(".json").read_text()) if glb.with_suffix(".json").is_file() else {
        "character": character,
        "pose": pose,
        "glb": str(glb),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    reg = json.loads(REGISTRY.read_text())
    zip_path = CACHE / "kenney_animated-characters-protagonists.zip"
    if args.force:
        for ch, spec in reg["characters"].items():
            for pose in ("standing", "seated"):
                p = MESH_DIR / spec[pose]
                if p.is_file():
                    p.unlink()
    _download(reg["download_url"], zip_path)
    extract = _extract(zip_path, CACHE / "protagonists")
    rows = []
    for character, spec in reg["characters"].items():
        for pose in ("standing", "seated"):
            rows.append(bake_one(extract, character, pose, spec, reg["fbx"]))
    payload = {
        "registry": str(REGISTRY),
        "zip_sha256": sha256_file(zip_path),
        "zip_bytes": zip_path.stat().st_size,
        "baked": rows,
        "license": reg["license"],
        "note": reg["note"],
    }
    (MESH_DIR / "fetch_log.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
