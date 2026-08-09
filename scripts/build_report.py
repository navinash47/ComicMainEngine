#!/usr/bin/env python3
"""Compile the ComicEngine LaTeX technical report to outputs/reports/."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX_DIR = ROOT / "reports" / "paper"
TEX = TEX_DIR / "comicengine_report.tex"
OUT_DIR = ROOT / "outputs" / "reports"
OUT_PDF = OUT_DIR / "comicengine_report.pdf"


def main() -> None:
    if not shutil.which("pdflatex"):
        raise SystemExit("pdflatex not found — install MacTeX / BasicTeX")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        "pdflatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        f"-output-directory={OUT_DIR}",
        str(TEX),
    ]
    # run twice for refs
    for i in range(2):
        print(f"pdflatex pass {i+1}…")
        r = subprocess.run(cmd, cwd=TEX_DIR, capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout[-4000:])
            print(r.stderr[-2000:])
            raise SystemExit(r.returncode)
    # pdflatex writes beside -output-directory using basename
    produced = OUT_DIR / "comicengine_report.pdf"
    if not produced.exists():
        # some installs write to tex dir
        alt = TEX_DIR / "comicengine_report.pdf"
        if alt.exists():
            shutil.copy2(alt, produced)
    print(f"wrote {produced}")
    print("Dashboard: http://127.0.0.1:8765/report")


if __name__ == "__main__":
    main()
