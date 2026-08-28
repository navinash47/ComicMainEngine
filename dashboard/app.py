"""Live usage analytics + TaskObserver + Stories + Phase 8.6 auth/feedback."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

from comicengine.analytics import analytics
from comicengine.auth_oauth import (
    clear_session,
    finish_google_login,
    login_redirect,
    oauth_configured,
    admin_user,
    require_admin,
    require_user,
    session_user,
    exchange_code,
    dev_login_user,
)
from comicengine.config import (
    AUTH_DEV_BYPASS,
    BETA_REQUIRE_LOGIN,
    OUTPUTS,
    SESSION_SECRET,
)
from comicengine.v2a_program import ARCHITECTURE_PATH, load_program as load_v2a_program
from comicengine.v2b_program import (
    ARCHITECTURE_PATH as V2B_ARCHITECTURE_PATH,
    SOURCE_PLAN_PATH as V2B_SOURCE_PLAN_PATH,
    load_program as load_v2b_program,
)
from comicengine.curation import curation, panel_editor_payload, regenerate_panel
from comicengine.feedback import feedback
from comicengine.images_gallery import gallery
from comicengine.library import load_catalog, rebuild_catalog
from comicengine.reviewers import reviewers
from comicengine.roi import roi_dashboard
from comicengine.stories import list_stories, load_story
from comicengine.tasks import observer
from comicengine.usage import UsageDB

STATIC = Path(__file__).resolve().parent / "static"
db = UsageDB()
tasks = observer
app = FastAPI(title="ComicEngine Usage")

app.mount("/static", StaticFiles(directory=STATIC), name="static")
OUTPUTS.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=OUTPUTS), name="media")


ADMIN_PREFIXES = (
    "/api/curation",
    "/api/library/refresh",
    "/api/analytics/rescan-images",
    "/api/feedback/export",
)


@app.middleware("http")
async def beta_auth_gate(request: Request, call_next):
    """Optional login wall. Default OFF so dashboard stats keep polling.

    Destructive curation APIs still use Depends(admin_user) when a session exists;
    set BETA_REQUIRE_LOGIN=1 only for a locked public beta host.
    """
    if not BETA_REQUIRE_LOGIN:
        return await call_next(request)

    path = request.url.path
    if (
        path.startswith("/static")
        or path.startswith("/auth")
        or path.startswith("/api/public")
        or path in {"/login", "/api/me", "/api/auth/status", "/favicon.ico"}
    ):
        return await call_next(request)

    user = session_user(request)
    if user:
        return await call_next(request)

    if path.startswith("/api/"):
        return JSONResponse({"detail": "login required"}, status_code=401)
    return RedirectResponse(url=f"/login?next={path}", status_code=302)


# Must be added AFTER @app.middleware("http") so SessionMiddleware is outermost
# (Starlette runs last-added middleware first).
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=False,
)


class TaskPatch(BaseModel):
    status: str | None = None
    progress: float | None = Field(default=None, ge=0, le=1)
    note: str | None = None
    title: str | None = None
    description: str | None = None


class FeedbackSubmit(BaseModel):
    answers: dict[str, Any]
    story_id: str = ""


@app.get("/login")
def login_page() -> FileResponse:
    return FileResponse(STATIC / "login.html")


@app.get("/auth/login")
def auth_login(request: Request, next: str = "/") -> RedirectResponse:
    return login_redirect(request, next_path=next or "/")


@app.get("/auth/callback")
def auth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if error:
        return RedirectResponse(url=f"/login?error={error}", status_code=302)
    if not code:
        raise HTTPException(status_code=400, detail="missing code")
    expected = request.session.get("oauth_state")
    if not expected or state != expected:
        raise HTTPException(status_code=400, detail="invalid oauth state")
    profile = exchange_code(code)
    finish_google_login(request, profile)
    nxt = request.session.pop("oauth_next", "/") or "/"
    request.session.pop("oauth_state", None)
    return RedirectResponse(url=nxt, status_code=302)


@app.get("/auth/dev-login")
def auth_dev_login(
    request: Request,
    next: str = "/library",
    email: str = "dev@local.test",
    name: str = "Dev Reviewer",
) -> RedirectResponse:
    if not AUTH_DEV_BYPASS:
        raise HTTPException(status_code=403, detail="enable AUTH_DEV_BYPASS=1 in .env")
    from comicengine.config import ADMIN_EMAILS

    admin = (not ADMIN_EMAILS) or email.lower() in ADMIN_EMAILS or email.endswith("@local.test")
    # Always admin for default local email so owner tools work offline
    if email == "dev@local.test":
        admin = True
    dev_login_user(request, email=email, name=name, admin=admin)
    return RedirectResponse(url=next or "/library", status_code=302)


@app.get("/auth/logout")
def auth_logout(request: Request) -> RedirectResponse:
    clear_session(request)
    return RedirectResponse(url="/login", status_code=302)


@app.get("/api/me")
def api_me(request: Request) -> dict[str, Any]:
    user = session_user(request)
    return {
        "authenticated": bool(user),
        "user": user,
        "oauth_configured": oauth_configured(),
        "auth_dev_bypass": AUTH_DEV_BYPASS,
        "beta_require_login": BETA_REQUIRE_LOGIN,
    }


@app.get("/api/auth/status")
def api_auth_status() -> dict[str, Any]:
    return {
        "oauth_configured": oauth_configured(),
        "auth_dev_bypass": AUTH_DEV_BYPASS,
        "beta_require_login": BETA_REQUIRE_LOGIN,
        "reviewers": reviewers.summary(),
        "feedback": feedback.summary(),
    }


@app.get("/")
def index() -> FileResponse:
    """Owner admin home — live usage / costs / recent calls (no auth)."""
    return FileResponse(STATIC / "index.html")


@app.get("/admin")
def admin_stats_page() -> FileResponse:
    """Alias for owner stats console (host privately; no login gate)."""
    return FileResponse(STATIC / "index.html")


@app.get("/stats")
def stats_page() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/analytics")
def analytics_page() -> FileResponse:
    return FileResponse(STATIC / "analytics.html")


@app.get("/images")
def images_page() -> FileResponse:
    return FileResponse(STATIC / "images.html")


@app.get("/library")
def library_page() -> FileResponse:
    return FileResponse(STATIC / "library.html")


@app.get("/feedback")
def feedback_page() -> FileResponse:
    return FileResponse(STATIC / "feedback.html")


@app.get("/reviewers")
def reviewers_page() -> FileResponse:
    return FileResponse(STATIC / "reviewers.html")


@app.get("/v2a")
def v2a_page() -> FileResponse:
    return FileResponse(STATIC / "v2a.html")


@app.get("/api/v2a/program")
def api_v2a_program() -> dict[str, Any]:
    return load_v2a_program()


@app.get("/v2a/architecture")
def v2a_architecture() -> FileResponse:
    if not ARCHITECTURE_PATH.is_file():
        raise HTTPException(status_code=404, detail="V2A architecture doc missing")
    return FileResponse(ARCHITECTURE_PATH, media_type="text/markdown; charset=utf-8")


@app.get("/v2b")
def v2b_page() -> FileResponse:
    return FileResponse(STATIC / "v2b.html")


@app.get("/api/v2b/program")
def api_v2b_program() -> dict[str, Any]:
    return load_v2b_program()


@app.get("/v2b/architecture")
def v2b_architecture() -> FileResponse:
    if not V2B_ARCHITECTURE_PATH.is_file():
        raise HTTPException(status_code=404, detail="V2B architecture doc missing")
    return FileResponse(V2B_ARCHITECTURE_PATH, media_type="text/markdown; charset=utf-8")


@app.get("/v2b/source-plan")
def v2b_source_plan() -> FileResponse:
    if not V2B_SOURCE_PLAN_PATH.is_file():
        raise HTTPException(status_code=404, detail="V2B source plan missing")
    return FileResponse(V2B_SOURCE_PLAN_PATH, media_type="text/markdown; charset=utf-8")


@app.get("/v2b/gate1")
def v2b_gate1_page() -> FileResponse:
    return FileResponse(STATIC / "v2b_gate1.html")


class V2bPrefIn(BaseModel):
    pair_id: str
    winner: str


@app.get("/api/v2b/gate1/pairs")
def api_v2b_gate1_pairs() -> list[dict[str, Any]]:
    from comicengine.v2b.eval.preferences import pair_catalog

    return pair_catalog()


@app.post("/api/v2b/preferences")
def api_v2b_preferences(body: V2bPrefIn) -> dict[str, Any]:
    from comicengine.v2b.eval.preferences import PAIRS, append_pref, agreement

    spec = next((p for p in PAIRS if p["id"] == body.pair_id), None)
    if spec is None:
        raise HTTPException(status_code=404, detail="unknown pair_id")
    if body.winner not in {"A", "B", "tie"}:
        raise HTTPException(status_code=400, detail="winner must be A, B, or tie")
    row = append_pref(
        pair_id=spec["id"],
        camera=spec["camera"],
        left=spec["left"],
        right=spec["right"],
        winner=body.winner,
        source="human",
    )
    return {"ok": True, "row": row, "agreement": agreement()}


@app.get("/api/v2b/b4/gallery")
def api_v2b_b4_gallery() -> dict[str, Any]:
    root = OUTPUTS / "v2b" / "himym_ep01"

    def url(path: Path) -> str | None:
        if not path.is_file():
            return None
        rel = path.resolve().relative_to(OUTPUTS.resolve())
        return "/media/" + str(rel).replace("\\", "/")

    dad_tt = sorted((root / "b4" / "turntable" / "dad").glob("*/beauty_01.png"))[:8]
    dad_style = sorted((root / "b4" / "dataset" / "dad").glob("*.png"))[:8]
    return {
        "b3_cam_a": url(root / "cam_a" / "panel_01.png"),
        "b4_cam_a": url(root / "b4" / "cam_a" / "panel_01.png"),
        "b4_beauty_a": url(root / "b4" / "cam_a" / "beauty_01.png"),
        "turntable": [url(p) for p in dad_tt if url(p)],
        "stylized": [url(p) for p in dad_style if url(p)],
    }


@app.get("/api/v2b/b5/gallery")
def api_v2b_b5_gallery() -> dict[str, Any]:
    root = OUTPUTS / "v2b" / "himym_ep01" / "b5"

    def url(path: Path) -> str | None:
        if not path.is_file():
            return None
        rel = path.resolve().relative_to(OUTPUTS.resolve())
        return "/media/" + str(rel).replace("\\", "/")

    return {
        "living_a": url(root / "living_room" / "cam_a" / "panel_01.png"),
        "living_beauty": url(root / "living_room" / "cam_a" / "beauty_01.png"),
        "lobby_wide": url(root / "grand_oriole_lobby" / "cam_wide" / "panel_01.png"),
        "lobby_close": url(root / "grand_oriole_lobby" / "cam_close" / "panel_01.png"),
        "lobby_beauty": url(root / "grand_oriole_lobby" / "cam_wide" / "beauty_01.png"),
    }


@app.get("/roi")
def roi_page() -> FileResponse:
    return FileResponse(STATIC / "roi.html")


@app.get("/api/roi")
def api_roi() -> dict[str, Any]:
    return roi_dashboard(db)


@app.get("/api/library")
def api_library(refresh: bool = Query(default=False)) -> dict[str, Any]:
    return load_catalog(refresh=refresh)


@app.post("/api/library/refresh")
def api_library_refresh(_admin: dict = Depends(admin_user)) -> dict[str, Any]:
    return {"ok": True, "catalog": rebuild_catalog()}


@app.get("/report")
def report_pdf() -> FileResponse:
    pdf = OUTPUTS / "reports" / "comicengine_report.pdf"
    if not pdf.exists():
        raise HTTPException(
            status_code=404,
            detail="Report PDF missing — run: python scripts/build_report.py",
        )
    return FileResponse(
        pdf,
        media_type="application/pdf",
        filename="comicengine_report.pdf",
        headers={"Content-Disposition": "inline; filename=comicengine_report.pdf"},
    )


@app.get("/api/images")
def api_images() -> dict[str, Any]:
    return gallery()


@app.get("/api/summary")
def summary() -> dict[str, Any]:
    snap = tasks.snapshot()
    dash = analytics.dashboard(limit=80)
    usage = db.summary()
    return {
        **usage,
        "taskobserver": snap,
        "romance": snap.get("romance") or tasks.romance_snapshot(),
        "stories": list_stories(),
        "analytics_preview": {
            "by_category": dash["stats"]["by_category"],
            "recommendations": dash["recommendations"][:5],
            "totals": dash["stats"].get("totals") or usage.get("totals"),
        },
        "live": {
            "total_spend_usd": (usage.get("totals") or {}).get("cost_usd"),
            "calls": (usage.get("totals") or {}).get("calls"),
            "romance_spend_usd": (snap.get("romance") or {}).get("spend_usd"),
            "updated_at": snap.get("updated_at"),
        },
        "reviewers": reviewers.summary(),
        "feedback": feedback.summary(),
    }


@app.get("/api/analytics")
def api_analytics(
    category: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
) -> dict[str, Any]:
    return analytics.dashboard(limit=limit, category=category)


@app.post("/api/analytics/rescan-images")
def api_rescan_images(_admin: dict = Depends(admin_user)) -> dict[str, Any]:
    result = analytics.rescan_image_quality()
    return {"ok": True, **result, "dashboard": analytics.dashboard(limit=100)}


@app.get("/api/tasks")
def list_tasks() -> dict[str, Any]:
    return tasks.snapshot()


@app.post("/api/tasks/refresh")
def refresh_tasks() -> dict[str, Any]:
    return tasks.snapshot()


@app.post("/api/tasks/{task_id}")
def patch_task(
    task_id: str, body: TaskPatch, _admin: dict = Depends(admin_user)
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if body.title is not None:
        kwargs["title"] = body.title
    if body.description is not None:
        kwargs["description"] = body.description
    if body.status is not None:
        kwargs["status"] = body.status
    if body.progress is not None:
        kwargs["progress"] = body.progress
    if body.note is not None:
        kwargs["meta"] = {"last_note": body.note}
    task = tasks.upsert(task_id, **kwargs)
    return {"ok": True, "task": task.as_dict(), "snapshot": tasks.snapshot()}


class CurationPatch(BaseModel):
    status: str | None = None
    note: str | None = None
    panel: int | None = None
    rating: int | None = None
    suggestions: str | None = None


class CurationRegenBody(BaseModel):
    panel: int
    note: str = ""
    prompt: str | None = None
    rating: int | None = None
    suggestions: str | None = None
    mark_rejected_first: bool = False


@app.get("/api/curation")
def api_curation(
    _admin: dict = Depends(admin_user),
    story_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> dict[str, Any]:
    return {
        "summary": curation.summary(),
        "items": curation.list(story_id=story_id, status=status),
    }


@app.post("/api/curation/seed")
def api_curation_seed(_admin: dict = Depends(admin_user)) -> dict[str, Any]:
    out = curation.seed_from_stories()
    return {"ok": True, **out, "catalog": rebuild_catalog()}


@app.get("/api/curation/{story_id}/panel/{panel}")
def api_curation_panel_editor(
    story_id: str, panel: int, _admin: dict = Depends(admin_user)
) -> dict[str, Any]:
    try:
        return panel_editor_payload(story_id, panel)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/curation/{story_id}")
def api_curation_upsert(
    story_id: str, body: CurationPatch, _admin: dict = Depends(admin_user)
) -> dict[str, Any]:
    if body.status is not None and body.status not in {
        "pending",
        "approved",
        "rejected",
        "regenerating",
        "regenerated",
    }:
        raise HTTPException(status_code=400, detail="invalid status")
    if body.rating is not None and not (1 <= int(body.rating) <= 5):
        raise HTTPException(status_code=400, detail="rating must be 1–5")
    item = curation.upsert(
        story_id=story_id,
        panel_index=body.panel,
        status=body.status,  # type: ignore[arg-type]
        note=body.note,
        rating=body.rating,
        suggestions=body.suggestions,
    )
    return {"ok": True, "item": item, "catalog": rebuild_catalog()}


@app.post("/api/curation/{story_id}/regenerate")
def api_curation_regen(
    story_id: str, body: CurationRegenBody, _admin: dict = Depends(admin_user)
) -> dict[str, Any]:
    try:
        result = regenerate_panel(
            story_id,
            body.panel,
            note=body.note or "",
            prompt=body.prompt,
            rating=body.rating,
            suggestions=body.suggestions,
            mark_rejected_first=body.mark_rejected_first,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {
        "ok": True,
        "item": result["item"],
        "method": result["render"].get("method"),
        "art_prompt": result.get("art_prompt"),
        "image_href": result.get("image_href"),
        "catalog": rebuild_catalog(),
    }


@app.get("/api/feedback/questions")
def api_feedback_questions() -> dict[str, Any]:
    return feedback.questionnaire_meta()


class PublicStoryFeedback(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    story_id: str
    overall_rating: int = Field(ge=1, le=5)
    overall_feedback: str = ""
    panels: list[dict[str, Any]] = Field(default_factory=list)


@app.post("/api/public/register")
def api_public_register(body: dict[str, Any]) -> dict[str, Any]:
    name = str(body.get("name") or "").strip()
    if not name or len(name) > 80:
        raise HTTPException(status_code=400, detail="name required (1–80 chars)")
    # Name-only reviewer (no Google). Stable id from lowercase name.
    import hashlib

    rid = "name:" + hashlib.sha256(name.lower().encode()).hexdigest()[:16]
    user = reviewers.upsert_from_google(
        {"sub": rid, "email": f"{rid}@name.local", "name": name, "picture": "", "locale": ""}
    )
    return {"ok": True, "reviewer": {"id": user["id"], "name": user["name"]}}


@app.post("/api/public/story-feedback")
def api_public_story_feedback(body: PublicStoryFeedback, request: Request) -> dict[str, Any]:
    from comicengine.story_feedback import story_feedback

    try:
        row = story_feedback.submit(
            name=body.name.strip(),
            story_id=body.story_id,
            overall_rating=body.overall_rating,
            overall_feedback=body.overall_feedback,
            panels=body.panels,
            user_agent=request.headers.get("user-agent", ""),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "response": row}


@app.get("/api/story-feedback")
def api_story_feedback_list(
    story_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
) -> dict[str, Any]:
    """Owner-only listing (open when BETA_REQUIRE_LOGIN=0). Reviewers cannot see others."""
    from comicengine.story_feedback import story_feedback

    return {
        "summary": story_feedback.summary(),
        "items": story_feedback.list(story_id=story_id, limit=limit),
    }


@app.get("/api/public/stories")
def api_public_stories() -> dict[str, Any]:
    from comicengine.public_catalog import public_stories

    return public_stories()


@app.get("/api/public/questionnaire")
def api_public_questionnaire_meta() -> dict[str, Any]:
    return feedback.public_questionnaire_meta()


class PublicQuestionnaire(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    story_id: str = ""
    answers: dict[str, Any] = Field(default_factory=dict)


@app.post("/api/public/questionnaire")
def api_public_questionnaire_submit(body: PublicQuestionnaire, request: Request) -> dict[str, Any]:
    import hashlib

    name = body.name.strip()
    rid = "name:" + hashlib.sha256(name.lower().encode()).hexdigest()[:16]
    user = reviewers.upsert_from_google(
        {"sub": rid, "email": f"{rid}@name.local", "name": name, "picture": "", "locale": ""}
    )
    try:
        row = feedback.submit(
            reviewer=user,
            answers=body.answers,
            story_id=body.story_id,
            user_agent=request.headers.get("user-agent", ""),
            public_subset=True,
            meta={"source": "local-review"},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "response": row, "summary": feedback.summary()}


@app.post("/api/feedback")
def api_feedback_submit(
    body: FeedbackSubmit, request: Request
) -> dict[str, Any]:
    # Prefer session user; else accept display name on body.answers meta
    user = session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="login required for Mom Test form")
    try:
        row = feedback.submit(
            reviewer=user,
            answers=body.answers,
            story_id=body.story_id,
            user_agent=request.headers.get("user-agent", ""),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "response": row, "summary": feedback.summary()}


@app.get("/api/feedback/list")
def api_feedback_list(
    reviewer_id: str | None = Query(default=None),
    story_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
) -> dict[str, Any]:
    return {
        "summary": feedback.summary(),
        "items": feedback.list(reviewer_id=reviewer_id, story_id=story_id, limit=limit),
    }


@app.get("/api/feedback/summary")
def api_feedback_summary() -> dict[str, Any]:
    return feedback.summary()


@app.get("/api/feedback/export")
def api_feedback_export(_admin: dict = Depends(admin_user)) -> dict[str, Any]:
    return feedback.export_for_future()


@app.get("/api/reviewers")
def api_reviewers() -> dict[str, Any]:
    return {"summary": reviewers.summary(), "items": reviewers.list()}


@app.get("/api/admin/crm")
def api_admin_crm(
    limit: int = Query(default=200, ge=1, le=2000),
) -> dict[str, Any]:
    """Local admin CRM: reviewers + story ratings + Mom Test forms + chart data."""
    from comicengine.story_feedback import story_feedback

    sf = story_feedback.list(limit=limit)
    mq = feedback.list(limit=limit)
    rev = reviewers.list(limit=500)
    by: dict[str, Any] = {}
    for r in rev:
        by[r["id"]] = {**r, "story_responses": [], "questionnaires": []}
    for item in sf:
        key = item.get("reviewer_key") or "unknown"
        name = item.get("reviewer_name") or "unknown"
        if key not in by:
            by[key] = {
                "id": key,
                "name": name,
                "email": "",
                "story_responses": [],
                "questionnaires": [],
            }
        by[key]["story_responses"].append(item)
        if not by[key].get("name"):
            by[key]["name"] = name
    for item in mq:
        rid = item.get("reviewer_id") or "unknown"
        if rid not in by:
            by[rid] = {
                "id": rid,
                "name": item.get("reviewer_name") or "unknown",
                "email": item.get("reviewer_email") or "",
                "story_responses": [],
                "questionnaires": [],
            }
        by[rid]["questionnaires"].append(item)

    people = []
    for p in by.values():
        overalls = [
            float(x.get("overall_rating"))
            for x in p["story_responses"]
            if x.get("overall_rating") is not None
        ]
        people.append(
            {
                **p,
                "stories_rated": len(p["story_responses"]),
                "questionnaire_count": len(p["questionnaires"]),
                "avg_overall": round(sum(overalls) / len(overalls), 2) if overalls else None,
            }
        )
    people.sort(key=lambda x: (x.get("name") or "").lower())

    ratings_hist = [0, 0, 0, 0, 0]
    by_story: dict[str, Any] = {}
    for item in sf:
        o = int(item.get("overall_rating") or 0)
        if 1 <= o <= 5:
            ratings_hist[o - 1] += 1
        sid = item.get("story_id") or "unknown"
        by_story.setdefault(sid, {"story_id": sid, "responses": 0, "sum": 0})
        by_story[sid]["responses"] += 1
        by_story[sid]["sum"] += o
    story_rows = [
        {
            "story_id": s["story_id"],
            "responses": s["responses"],
            "avg_overall": round(s["sum"] / s["responses"], 2) if s["responses"] else 0,
        }
        for s in by_story.values()
    ]

    return {
        "summary": {
            "reviewers": len(rev),
            "story_feedback": len(sf),
            "questionnaires": len(mq),
            "people": len(people),
        },
        "people": people,
        "story_feedback": sf,
        "questionnaires": mq,
        "charts": {"ratings_hist": ratings_hist, "by_story": story_rows},
        "usage": (db.summary() or {}).get("totals"),
    }


@app.get("/api/stories")
def api_stories() -> dict[str, Any]:
    return {"stories": list_stories()}


@app.get("/api/stories/{story_id}")
def api_story(story_id: str) -> dict[str, Any]:
    story = load_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="story not found")
    return story


@app.get("/review", response_class=HTMLResponse)
def public_review_home() -> FileResponse:
    return FileResponse(STATIC / "review" / "index.html")


@app.get("/review/questionnaire", response_class=HTMLResponse)
def public_review_questionnaire() -> FileResponse:
    return FileResponse(STATIC / "review" / "questionnaire.html")


@app.get("/review/{story_id}", response_class=HTMLResponse)
def public_review_story(story_id: str) -> FileResponse:
    return FileResponse(STATIC / "review" / "story.html")


@app.get("/stories/{story_id}", response_class=HTMLResponse)
def story_page(story_id: str) -> HTMLResponse:
    return HTMLResponse((STATIC / "story.html").read_text())
