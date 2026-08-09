"""Live usage analytics + TaskObserver + Stories. Polls SQLite every few seconds."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from comicengine.analytics import analytics
from comicengine.stories import list_stories, load_story
from comicengine.tasks import observer
from comicengine.usage import UsageDB

STATIC = Path(__file__).resolve().parent / "static"
db = UsageDB()
tasks = observer
app = FastAPI(title="ComicEngine Usage")

app.mount("/static", StaticFiles(directory=STATIC), name="static")


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
