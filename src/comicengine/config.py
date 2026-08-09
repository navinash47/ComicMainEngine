from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
# Project .env first; ~/.omniroute/.env can supply OMNIROUTE_API_KEY if missing
load_dotenv(ROOT / ".env")
load_dotenv(Path.home() / ".omniroute" / ".env", override=False)


def env(name: str, default: str | None = None) -> str | None:
    val = os.getenv(name, default)
    if val is None:
        return None
    return val.strip() or None


USAGE_DB_PATH = Path(env("USAGE_DB_PATH", str(ROOT / "data" / "usage.db")))
DASHBOARD_PORT = int(env("DASHBOARD_PORT", "8765") or "8765")
OUTPUTS = ROOT / "outputs"

# OmniRoute — local router (Cursor Override OpenAI Base URL → http://127.0.0.1:20128/v1)
USE_OMNIROUTE = (env("USE_OMNIROUTE", "1") or "1").lower() in {"1", "true", "yes", "on"}
OMNIROUTE_BASE_URL = (env("OMNIROUTE_BASE_URL", "http://127.0.0.1:20128") or "http://127.0.0.1:20128").rstrip("/")


def omniroute_api_key() -> str | None:
    """Same key you paste into Cursor Models → OpenAI API Key when overriding to :20128/v1."""
    return env("OMNIROUTE_API_KEY") or env("OPENAI_API_KEY")


def omniroute_openai_base() -> str:
    return f"{OMNIROUTE_BASE_URL}/v1"


def omniroute_anthropic_base() -> str:
    # Anthropic SDK appends /v1/messages; OmniRoute Anthropic surface is the root.
    return OMNIROUTE_BASE_URL


def routing_label() -> str:
    return "omniroute" if USE_OMNIROUTE else "direct"


def fal_api_key() -> str | None:
    """fal.ai key — SDK reads FAL_KEY; project .env may use FAL_API_KEY."""
    return env("FAL_KEY") or env("FAL_API_KEY")
