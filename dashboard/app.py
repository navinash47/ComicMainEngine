"""Live usage analytics + TaskObserver + Stories. Polls SQLite every few seconds."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from comicengine.analytics import analytics
from comicengine.config import OUTPUTS
from comicengine.images_gallery import gallery
from comicengine.curation import curation, panel_editor_payload, regenerate_panel
from comicengine.library import load_catalog, rebuild_catalog
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


class TaskPatch(BaseModel):
    status: str | None = None
    progress: float | None = Field(default=None, ge=0, le=1)
    note: str | None = None
    title: str | None = None
    description: str | None = None


@app.get("/")
def index() -> FileResponse:
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
def api_library_refresh() -> dict[str, Any]:
    return {"ok": True, "catalog": rebuild_catalog()}


@app.get("/report")
def report_pdf() -> FileResponse:
    """Two-column LaTeX technical report (rebuild: python scripts/build_report.py)."""
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
    return {
        **db.summary(),
        "taskobserver": snap,
        "stories": list_stories(),
        "analytics_preview": {
            "by_category": dash["stats"]["by_category"],
            "recommendations": dash["recommendations"][:5],
        },
    }


@app.get("/api/analytics")
def api_analytics(
    category: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
) -> dict[str, Any]:
    return analytics.dashboard(limit=limit, category=category)


@app.post("/api/analytics/rescan-images")
def api_rescan_images() -> dict[str, Any]:
    result = analytics.rescan_image_quality()
    return {"ok": True, **result, "dashboard": analytics.dashboard(limit=100)}


@app.get("/api/tasks")
def list_tasks() -> dict[str, Any]:
    return tasks.snapshot()


@app.post("/api/tasks/refresh")
def refresh_tasks() -> dict[str, Any]:
    return tasks.snapshot()


@app.post("/api/tasks/{task_id}")
def patch_task(task_id: str, body: TaskPatch) -> dict[str, Any]:
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
    story_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> dict[str, Any]:
    return {
        "summary": curation.summary(),
        "items": curation.list(story_id=story_id, status=status),
    }


@app.post("/api/curation/seed")
def api_curation_seed() -> dict[str, Any]:
    out = curation.seed_from_stories()
    return {"ok": True, **out, "catalog": rebuild_catalog()}


@app.get("/api/curation/{story_id}/panel/{panel}")
def api_curation_panel_editor(story_id: str, panel: int) -> dict[str, Any]:
    try:
        return panel_editor_payload(story_id, panel)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/curation/{story_id}")
def api_curation_upsert(story_id: str, body: CurationPatch) -> dict[str, Any]:
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
def api_curation_regen(story_id: str, body: CurationRegenBody) -> dict[str, Any]:
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


@app.get("/api/stories")
def api_stories() -> dict[str, Any]:
    return {"stories": list_stories()}


@app.get("/api/stories/{story_id}")
def api_story(story_id: str) -> dict[str, Any]:
    story = load_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="story not found")
    return story


@app.get("/stories/{story_id}", response_class=HTMLResponse)
def story_page(story_id: str) -> HTMLResponse:
    return HTMLResponse((STATIC / "story.html").read_text())
