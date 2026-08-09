#!/usr/bin/env python3
"""Start live usage dashboard at http://127.0.0.1:8765"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "dashboard")]

import uvicorn

from comicengine.config import DASHBOARD_HOST, DASHBOARD_PORT


def main() -> None:
    uvicorn.run("app:app", host=DASHBOARD_HOST, port=DASHBOARD_PORT, reload=False)


if __name__ == "__main__":
    main()
