from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def env(name: str, default: str | None = None) -> str | None:
    val = os.getenv(name, default)
    if val is None:
        return None
    return val.strip() or None


USAGE_DB_PATH = Path(env("USAGE_DB_PATH", str(ROOT / "data" / "usage.db")))
DASHBOARD_PORT = int(env("DASHBOARD_PORT", "8765") or "8765")
OUTPUTS = ROOT / "outputs"
