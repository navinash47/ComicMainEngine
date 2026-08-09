"""Phase 7 / 7.5 — assemble panels into vertical webtoon PNG + multi-page PDF."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from PIL import Image, ImageDraw, ImageFont

from comicengine.config import OUTPUTS, ROOT
from comicengine.episode_schema import Episode

PHASE5 = OUTPUTS / "phase5"
PHASE6 = OUTPUTS / "phase6"
PHASE7 = OUTPUTS / "phase7"
PHASE75 = OUTPUTS / "phase7.5"

Edition = Literal["composed", "image_only"]

FONT_CANDIDATES = [
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    Path("/Library/Fonts/Arial.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
]


def _font(size: int) -> ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _panel_source(
    episode: Episode,
    story_id: str,
    index: int,
    *,
    edition: Edition,
) -> Path | None:
    panel = next((p for p in episode.panels if p.index == index), None)
    candidates: list[Path] = []
    if edition == "image_only":
        # Raw Phase 5 art only — no speech bubbles / caption bars
        if panel and panel.image_path:
            p = Path(panel.image_path)
            candidates.append(p if p.is_absolute() else ROOT / p)
        candidates.append(PHASE5 / story_id / f"panel_{index:02d}.png")
    else:
        if panel and panel.composed_image_path:
            p = Path(panel.composed_image_path)
            candidates.append(p if p.is_absolute() else ROOT / p)
        candidates.append(PHASE6 / story_id / f"panel_{index:02d}.png")
        if panel and panel.image_path:
            p = Path(panel.image_path)
            candidates.append(p if p.is_absolute() else ROOT / p)
        candidates.append(PHASE5 / story_id / f"panel_{index:02d}.png")
    for c in candidates:
        if c.is_file() and c.stat().st_size > 1000:
            return c
    return None


def _cover(title: str, subtitle: str, width: int, height: int = 360, *, badge: str = "") -> Image.Image:
    img = Image.new("RGB", (width, height), (18, 18, 22))
    draw = ImageDraw.Draw(img)
    title_font = _font(36)
    sub_font = _font(20)
    brand_font = _font(16)
    brand = "ComicEngine · onceuponatime"
    if badge:
        brand = f"{brand} · {badge}"
    draw.text((40, 48), brand, font=brand_font, fill=(232, 176, 122))
    words = title.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=title_font) < width - 80:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    y = 110
    for line in lines[:4]:
        draw.text((40, y), line, font=title_font, fill=(245, 242, 235))
        y += 46
    draw.text((40, min(y + 12, height - 60)), subtitle[:140], font=sub_font, fill=(170, 168, 160))
    return img


def assemble_episode(
    episode: Episode,
    *,
    story_id: str,
    target_width: int = 900,
    gutter: int = 18,
    skip_existing: bool = True,
    edition: Edition = "composed",
) -> dict[str, Any]:
    """Assemble episode.

    edition='composed'  → Phase 7  (bubbles/captions from Phase 6)
    edition='image_only' → Phase 7.5 (raw Phase 5 panels only)
    """
    if edition == "image_only":
        out_dir = PHASE75 / story_id
        phase_label = "phase7.5"
        badge = "Only Image"
        webtoon_name = "webtoon_image_only.png"
        pdf_name = "episode_image_only.pdf"
    else:
        out_dir = PHASE7 / story_id
        phase_label = "phase7"
        badge = "Reader edition"
        webtoon_name = "webtoon.png"
        pdf_name = "episode.pdf"

    out_dir.mkdir(parents=True, exist_ok=True)
    webtoon_path = out_dir / webtoon_name
    pdf_path = out_dir / pdf_name
    manifest_path = out_dir / "manifest.json"

    if (
        skip_existing
        and webtoon_path.is_file()
        and pdf_path.is_file()
        and webtoon_path.stat().st_size > 1000
        and pdf_path.stat().st_size > 1000
    ):
        rel_w = _rel(webtoon_path)
        rel_p = _rel(pdf_path)
        if edition == "composed":
            episode.webtoon_path = rel_w
            episode.pdf_path = rel_p
        else:
            episode.webtoon_image_only_path = rel_w
            episode.pdf_image_only_path = rel_p
        return {
            "story_id": story_id,
            "edition": edition,
            "status": "skipped_existing",
            "webtoon_path": rel_w,
            "pdf_path": rel_p,
            "webtoon_href": f"/media/{phase_label}/{story_id}/{webtoon_name}",
            "pdf_href": f"/media/{phase_label}/{story_id}/{pdf_name}",
            "panel_count": len(episode.panels),
            "assembled_panels": len(episode.panels),
            "missing_panels": [],
        }

    panels = sorted(episode.panels, key=lambda p: p.index)
    images: list[Image.Image] = []
    used: list[str] = []
    missing: list[int] = []

    cover_sub = episode.topic or story_id
    if edition == "image_only":
        cover_sub = f"Only Image edition · {cover_sub}"
    images.append(_cover(episode.title, cover_sub, target_width, badge=badge))

    for panel in panels:
        src = _panel_source(episode, story_id, panel.index, edition=edition)
        if not src:
            missing.append(panel.index)
            continue
        im = Image.open(src).convert("RGB")
        if im.width != target_width:
            new_h = max(1, int(im.height * (target_width / im.width)))
            im = im.resize((target_width, new_h), Image.Resampling.LANCZOS)
        images.append(im)
        used.append(_rel(src))

    if len(images) <= 1:
        raise RuntimeError(f"no panels found to assemble for {story_id} ({edition})")

    total_h = sum(im.height for im in images) + gutter * (len(images) - 1)
    canvas = Image.new("RGB", (target_width, total_h), (12, 12, 16))
    y = 0
    for im in images:
        canvas.paste(im, (0, y))
        y += im.height + gutter

    max_png_h = 65000
    if canvas.height > max_png_h:
        scale = max_png_h / canvas.height
        canvas = canvas.resize(
            (max(1, int(canvas.width * scale)), max_png_h),
            Image.Resampling.LANCZOS,
        )

    canvas.save(webtoon_path, format="PNG", optimize=True)
    images[0].save(
        pdf_path,
        "PDF",
        resolution=100.0,
        save_all=True,
        append_images=images[1:],
    )

    rel_w = _rel(webtoon_path)
    rel_p = _rel(pdf_path)
    manifest = {
        "story_id": story_id,
        "title": episode.title,
        "edition": edition,
        "status": "ok",
        "webtoon_path": rel_w,
        "pdf_path": rel_p,
        "webtoon_href": f"/media/{phase_label}/{story_id}/{webtoon_name}",
        "pdf_href": f"/media/{phase_label}/{story_id}/{pdf_name}",
        "panel_count": len(panels),
        "assembled_panels": len(used),
        "missing_panels": missing,
        "sources": used,
        "webtoon_size": list(canvas.size),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))

    if edition == "composed":
        episode.webtoon_path = rel_w
        episode.pdf_path = rel_p
    else:
        episode.webtoon_image_only_path = rel_w
        episode.pdf_image_only_path = rel_p
    try:
        from comicengine.usage import UsageDB

        UsageDB().log_local(
            phase="phase7.5" if edition == "image_only" else "phase7",
            purpose=f"assemble_{edition}",
            note=f"assembled {story_id} ({edition})",
            meta={"story_id": story_id, "edition": edition, "panels": len(used)},
        )
    except Exception:  # noqa: BLE001
        pass
    return manifest
