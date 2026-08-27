"""Invoke Blender as a subprocess. Not MCP."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from comicengine.config import ROOT

SCRIPT = Path(__file__).resolve().parent / "himym_p1.py"

CANDIDATES = (
    os.environ.get("BLENDER_BIN"),
    "/opt/homebrew/bin/blender",
    "/Applications/Blender.app/Contents/MacOS/Blender",
    shutil.which("blender"),
)


def blender_bin() -> Path:
    for raw in CANDIDATES:
        if not raw:
            continue
        p = Path(raw)
        if p.is_file():
            return p
    raise FileNotFoundError(
        "Blender not found. Install with `brew install --cask blender` "
        "or set BLENDER_BIN to the binary."
    )


def render_himym_p1(out_png: Path) -> Path:
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(blender_bin()),
        "--background",
        "--factory-startup",
        "--python",
        str(SCRIPT),
        "--",
        "--out",
        str(out_png),
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not out_png.is_file():
        raise RuntimeError(
            "Blender render failed.\n"
            f"cmd: {cmd}\n"
            f"exit: {proc.returncode}\n"
            f"stdout:\n{proc.stdout[-4000:]}\n"
            f"stderr:\n{proc.stderr[-4000:]}"
        )
    return out_png
