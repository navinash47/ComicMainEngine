"""Phase 8.6 — session helpers + Google OAuth (Authlib optional; httpx fallback)."""

from __future__ import annotations

import secrets
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, Request
from starlette.responses import RedirectResponse

from comicengine.config import (
    AUTH_DEV_BYPASS,
    GOOGLE_OAUTH_CLIENT_ID,
    GOOGLE_OAUTH_CLIENT_SECRET,
    PUBLIC_BASE_URL,
)
from comicengine.reviewers import reviewers

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def oauth_configured() -> bool:
    return bool(GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET)


def callback_url() -> str:
    return f"{PUBLIC_BASE_URL}/auth/callback"


def google_authorize_url(state: str) -> str:
    if not oauth_configured():
        raise RuntimeError("GOOGLE_OAUTH_CLIENT_ID / SECRET not set — see docs/BETA_SETUP.md")
    params = {
        "client_id": GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": callback_url(),
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "include_granted_scopes": "true",
        "prompt": "select_account",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str) -> dict[str, Any]:
    data = {
        "code": code,
        "client_id": GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
        "redirect_uri": callback_url(),
        "grant_type": "authorization_code",
    }
    with httpx.Client(timeout=30.0) as client:
        tok = client.post(GOOGLE_TOKEN_URL, data=data)
        tok.raise_for_status()
        token = tok.json()
        access = token.get("access_token")
        if not access:
            raise RuntimeError("No access_token from Google")
        ui = client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access}"},
        )
        ui.raise_for_status()
        return ui.json()


def session_user(request: Request) -> dict[str, Any] | None:
    raw = request.session.get("user")
    return dict(raw) if isinstance(raw, dict) and raw.get("email") else None


def set_session_user(request: Request, user: dict[str, Any]) -> None:
    request.session["user"] = {
        "id": user.get("id"),
        "email": user.get("email"),
        "name": user.get("name"),
        "picture": user.get("picture"),
        "is_admin": bool(user.get("is_admin")),
    }


def clear_session(request: Request) -> None:
    request.session.clear()


def require_user(request: Request) -> dict[str, Any]:
    user = session_user(request)
    if user:
        return user
    raise HTTPException(status_code=401, detail="login required")


def require_admin(request: Request) -> dict[str, Any]:
    user = require_user(request)
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="admin only")
    return user


def admin_user(request: Request) -> dict[str, Any]:
    """Owner tooling: open access when login wall is off; else require admin session."""
    from comicengine.config import BETA_REQUIRE_LOGIN

    if not BETA_REQUIRE_LOGIN:
        user = session_user(request)
        return user or {
            "id": "local-admin",
            "email": "admin@local",
            "name": "Admin",
            "is_admin": True,
        }
    return require_admin(request)


def login_redirect(request: Request, next_path: str = "/") -> RedirectResponse:
    if AUTH_DEV_BYPASS and not oauth_configured():
        return RedirectResponse(url=f"/auth/dev-login?next={next_path}", status_code=302)
    state = secrets.token_urlsafe(24)
    request.session["oauth_state"] = state
    request.session["oauth_next"] = next_path or "/"
    return RedirectResponse(url=google_authorize_url(state), status_code=302)


def finish_google_login(request: Request, profile: dict[str, Any]) -> dict[str, Any]:
    user = reviewers.upsert_from_google(profile)
    set_session_user(request, user)
    return user


def dev_login_user(
    request: Request,
    *,
    email: str = "dev@local.test",
    name: str = "Dev Reviewer",
    admin: bool = True,
) -> dict[str, Any]:
    if not AUTH_DEV_BYPASS:
        raise HTTPException(status_code=403, detail="AUTH_DEV_BYPASS disabled")
    profile = {
        "sub": f"dev:{email}",
        "email": email,
        "name": name,
        "picture": "",
        "locale": "en",
    }
    user = reviewers.upsert_from_google(profile)
    # Force admin flag for local owner when requested
    if admin and not user.get("is_admin"):
        from comicengine.config import ADMIN_EMAILS

        if email.lower() in ADMIN_EMAILS or admin:
            with reviewers.connect() as conn:
                conn.execute("UPDATE reviewer SET is_admin=1 WHERE id=?", (user["id"],))
            user = reviewers.get(user["id"]) or user
            user["is_admin"] = True
    set_session_user(request, user)
    return user
