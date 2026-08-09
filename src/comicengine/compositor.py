"""Phase 6 — speech-bubble / caption compositor (Pillow)."""

from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from comicengine.config import OUTPUTS, ROOT
from comicengine.episode_schema import Episode, Panel

PHASE6 = OUTPUTS / "phase6"

FONT_CANDIDATES = [
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    Path("/Library/Fonts/Arial.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    Path("/Library/Fonts/Arial Unicode.ttf"),
    Path("/System/Library/Fonts/Helvetica.ttc"),
]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _wrap(text: str, width: int) -> list[str]:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return []
    return textwrap.wrap(text, width=width, break_long_words=True, break_on_hyphens=False)


def _parse_dialogue(dialogue: str) -> list[tuple[str | None, str]]:
    """Return list of (speaker, line). Plain lines have speaker=None."""
    lines: list[tuple[str | None, str]] = []
    for raw in (dialogue or "").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        if ":" in raw:
            speaker, rest = raw.split(":", 1)
            speaker = speaker.strip()
            rest = rest.strip()
            if speaker and rest and len(speaker) < 40:
                lines.append((speaker, rest))
                continue
        lines.append((None, raw))
    return lines


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def _draw_round_rect(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    *,
    fill: tuple[int, ...],
    outline: tuple[int, ...] = (20, 20, 24, 255),
    width: int = 2,
    radius: int = 18,
) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def _draw_bubble(
    draw: ImageDraw.ImageDraw,
    *,
    x: int,
    y: int,
    max_w: int,
    speaker: str | None,
    text: str,
    body_font: ImageFont.ImageFont,
    label_font: ImageFont.ImageFont,
    align_right: bool = False,
) -> int:
    """Draw one bubble; return bottom y."""
    pad_x, pad_y = 16, 12
    wrap_cols = max(18, min(42, max_w // 12))
    body_lines = _wrap(text, wrap_cols)
    if not body_lines and not speaker:
        return y

    label = (speaker or "").replace("_", " ").title()
    content_w = 0
    content_h = 0
    if label:
        lw, lh = _text_size(draw, label, label_font)
        content_w = max(content_w, lw)
        content_h += lh + 4
    line_sizes: list[tuple[int, int]] = []
    for line in body_lines:
        tw, th = _text_size(draw, line, body_font)
        line_sizes.append((tw, th))
        content_w = max(content_w, tw)
        content_h += th + 2

    box_w = min(max_w, content_w + pad_x * 2)
    box_h = content_h + pad_y * 2
    left = x if not align_right else x - box_w
    left = max(12, left)
    right = left + box_w
    top = y
    bottom = top + box_h

    _draw_round_rect(
        draw,
        (left, top, right, bottom),
        fill=(252, 250, 245, 235),
        outline=(28, 28, 34, 255),
        width=2,
        radius=16,
    )
    # small tail
    mid = left + box_w // 3 if not align_right else right - box_w // 3
    draw.polygon(
        [(mid - 10, bottom - 2), (mid + 10, bottom - 2), (mid, bottom + 12)],
        fill=(252, 250, 245, 235),
        outline=(28, 28, 34, 255),
    )

    cy = top + pad_y
    cx = left + pad_x
    if label:
        draw.text((cx, cy), label, font=label_font, fill=(120, 72, 40, 255))
        _, lh = _text_size(draw, label, label_font)
        cy += lh + 4
    for (line, (_tw, th)) in zip(body_lines, line_sizes):
        draw.text((cx, cy), line, font=body_font, fill=(18, 18, 22, 255))
        cy += th + 2
    return bottom + 18


def _draw_caption_bar(
    base: Image.Image,
    caption: str,
    *,
    font: ImageFont.ImageFont,
) -> Image.Image:
    if not (caption or "").strip():
        return base
    img = base.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = img.size
    lines = _wrap(caption, max(24, w // 14))
    if not lines:
        return base
    line_h = _text_size(draw, "Ag", font)[1] + 4
    bar_h = line_h * len(lines) + 28
    top = h - bar_h - 10
    draw.rounded_rectangle(
        (14, top, w - 14, h - 10),
        radius=14,
        fill=(12, 12, 16, 200),
        outline=(232, 176, 122, 180),
        width=2,
    )
    y = top + 14
    for line in lines:
        tw, _ = _text_size(draw, line, font)
        draw.text(((w - tw) / 2, y), line, font=font, fill=(245, 242, 235, 255))
        y += line_h
    return Image.alpha_composite(img, overlay)


def compose_panel(panel: Panel, src: Path, dest: Path) -> dict[str, Any]:
    """Overlay dialogue bubbles + caption bar onto a panel image."""
    src = Path(src)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    base = Image.open(src).convert("RGBA")
    w, h = base.size
    scale = max(w, h) / 1024.0
    body_font = _font(max(16, int(22 * scale)))
    label_font = _font(max(13, int(16 * scale)))
    caption_font = _font(max(15, int(20 * scale)))

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    dialogues = _parse_dialogue(panel.dialogue)
    y = int(24 * scale)
    max_bubble_w = int(w * 0.62)
    for i, (speaker, text) in enumerate(dialogues[:3]):  # cap bubbles for clarity
        align_right = i % 2 == 1
        x = int(w * 0.06) if not align_right else int(w * 0.94)
        y = _draw_bubble(
            draw,
            x=x,
            y=y,
            max_w=max_bubble_w,
            speaker=speaker,
            text=text,
            body_font=body_font,
            label_font=label_font,
            align_right=align_right,
        )
        if y > h * 0.55:
            break

    composed = Image.alpha_composite(base, overlay)
    composed = _draw_caption_bar(composed, panel.caption, font=caption_font)
    # keep file size reasonable as RGB PNG
    composed.convert("RGB").save(dest, format="PNG", optimize=True)
    return {
        "index": panel.index,
        "source": str(src),
        "composed": str(dest),
        "bubbles": len(dialogues),
        "has_caption": bool((panel.caption or "").strip()),
        "status": "ok",
    }


def bridge_text(episode: Episode, panel: Panel, prev: Panel | None) -> str:
    """Short interstitial narration for the webpage reader."""
    parts: list[str] = []
    if prev is None:
        parts.append(episode.narrative_summary.strip()[:420] if episode.narrative_summary else "")
    # Prefer scene description as connective tissue
    scene = (panel.scene_description or "").strip()
    if scene:
        parts.append(scene)
    emotion = (panel.emotion or "").strip()
    if emotion and emotion.lower() not in {"warm", "serious", ""}:
        parts.append(f"Mood shifts: {emotion}.")
    # Deduplicate empties
    out = " ".join(p for p in parts if p)
    return out


def compose_episode(
    episode: Episode,
    *,
    story_id: str,
    skip_existing: bool = True,
) -> dict[str, Any]:
    out_dir = PHASE6 / story_id
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    bridges: list[dict[str, Any]] = []
    prev: Panel | None = None

    for panel in sorted(episode.panels, key=lambda p: p.index):
        if not panel.image_path:
            rows.append({"index": panel.index, "status": "skip_no_source"})
            continue
        src = ROOT / panel.image_path if not Path(panel.image_path).is_absolute() else Path(panel.image_path)
        if not src.is_file():
            # also accept under OUTPUTS
            alt = OUTPUTS / Path(panel.image_path).name
            src = alt if alt.is_file() else src
        if not src.is_file():
            # try phase5 convention
            src = OUTPUTS / "phase5" / story_id / f"panel_{panel.index:02d}.png"
        dest = out_dir / f"panel_{panel.index:02d}.png"
        bridges.append(
            {
                "before_panel": panel.index,
                "text": bridge_text(episode, panel, prev),
            }
        )
        if skip_existing and dest.is_file() and dest.stat().st_size > 1000:
            panel.composed_image_path = str(dest.relative_to(ROOT))
            rows.append(
                {
                    "index": panel.index,
                    "status": "skipped_existing",
                    "composed": str(dest),
                }
            )
            prev = panel
            continue
        if not src.is_file():
            rows.append({"index": panel.index, "status": "error", "error": f"missing {src}"})
            prev = panel
            continue
        row = compose_panel(panel, src, dest)
        panel.composed_image_path = str(dest.relative_to(ROOT))
        rows.append(row)
        prev = panel

    manifest = {
        "story_id": story_id,
        "title": episode.title,
        "ok": sum(1 for r in rows if r.get("status") in {"ok", "skipped_existing"}),
        "errors": sum(1 for r in rows if r.get("status") == "error"),
        "panels": rows,
        "bridges": bridges,
    }
    (out_dir / "manifest.json").write_text(
        __import__("json").dumps(manifest, indent=2),
        encoding="utf-8",
    )
    try:
        from comicengine.usage import UsageDB

        UsageDB().log_local(
            phase="phase6",
            purpose="compose_episode",
            note=f"composed {manifest['ok']} panels for {story_id}",
            meta={"story_id": story_id, "ok": manifest["ok"], "errors": manifest["errors"]},
        )
    except Exception:  # noqa: BLE001
        pass
    return manifest
