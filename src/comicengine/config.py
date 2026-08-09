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
DASHBOARD_HOST = env("DASHBOARD_HOST", "127.0.0.1") or "127.0.0.1"
OUTPUTS = ROOT / "outputs"
PUBLIC_BASE_URL = (env("PUBLIC_BASE_URL", f"http://{DASHBOARD_HOST}:{DASHBOARD_PORT}") or "").rstrip("/")

# Phase 8.6 — Google OAuth / sessions (see docs/BETA_SETUP.md)
SESSION_SECRET = env("SESSION_SECRET") or "dev-insecure-change-me"
GOOGLE_OAUTH_CLIENT_ID = env("GOOGLE_OAUTH_CLIENT_ID") or env("GOOGLE_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = env("GOOGLE_OAUTH_CLIENT_SECRET") or env("GOOGLE_CLIENT_SECRET")
AUTH_DEV_BYPASS = (env("AUTH_DEV_BYPASS", "0") or "0").lower() in {"1", "true", "yes", "on"}
BETA_REQUIRE_LOGIN = (env("BETA_REQUIRE_LOGIN", "0") or "0").lower() in {"1", "true", "yes", "on"}
ADMIN_EMAILS = {
    e.strip().lower()
    for e in (env("ADMIN_EMAILS", "") or "").split(",")
    if e.strip()
}

# Phase 10 — Cloudflare R2 / Pages
CF_ACCOUNT_ID = env("CF_ACCOUNT_ID")
CF_R2_ACCESS_KEY_ID = env("CF_R2_ACCESS_KEY_ID")
CF_R2_SECRET_ACCESS_KEY = env("CF_R2_SECRET_ACCESS_KEY")
CF_R2_BUCKET = env("CF_R2_BUCKET", "comicengine-beta")
CF_PAGES_PROJECT = env("CF_PAGES_PROJECT", "comicengine-beta")
BETA_PUBLISH_APPROVED_ONLY = (env("BETA_PUBLISH_APPROVED_ONLY", "1") or "1").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

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
