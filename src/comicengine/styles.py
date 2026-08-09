"""Style presets for Phase 2 bake-off + active style lock."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from comicengine.config import ROOT

LOCK_PATH = ROOT / "data" / "style_lock.json"


@dataclass(frozen=True)
class StylePreset:
    id: str
    label: str
    suffix: str
    negative: str
    vibe: str  # for LLM judge


PRESETS: dict[str, StylePreset] = {
    "korean_manhwa": StylePreset(
        id="korean_manhwa",
        label="Korean manhwa webtoon",
        suffix=(
            "Korean manhwa webtoon illustration style, clean ink line art, soft cel shading, "
            "expressive eyes, polished digital comic coloring, warm cinematic lighting, "
            "vertical webtoon panel composition, all-ages gentle mood, "
            "NOT photorealistic, NOT western cartoon, NOT chibi, NOT horror"
        ),
        negative="photorealistic, 3d render, uncanny, horror, gore, blurry, watermark",
        vibe="immersive webtoon drama with clear character emotion, modern youth energy",
    ),
    "painterly_storybook": StylePreset(
        id="painterly_storybook",
        label="Painterly bedtime storybook",
        suffix=(
            "warm painterly children's-storybook illustration, soft gouache textures, "
            "golden bedtime lighting, gentle rounded shapes, cinematic picture-book composition, "
            "NOT anime, NOT photorealistic"
        ),
        negative="anime, manga, photorealistic, horror, gore, harsh contrast",
        vibe="cozy bedtime dad-to-daughter warmth, soft and safe",
    ),
    "graphic_novel": StylePreset(
        id="graphic_novel",
        label="Soft graphic novel",
        suffix=(
            "soft realistic graphic-novel illustration, muted cinematic colors, "
            "careful inking, emotionally grounded faces, Indie comic look, all-ages, "
            "NOT photorealistic, NOT anime"
        ),
        negative="anime, chibi, photorealistic, horror, gore, loud neon",
        vibe="serious civic storytelling with human dignity",
    ),
    "watercolor_editorial": StylePreset(
        id="watercolor_editorial",
        label="Watercolor editorial",
        suffix=(
            "soft watercolor editorial illustration, paper texture, gentle washes, "
            "expressive but respectful portraiture, magazine feature art, all-ages"
        ),
        negative="anime, harsh cel shading, photorealistic, horror, gore",
        vibe="reflective documentary emotion, thoughtful and calm",
    ),
}


def get_preset(style_id: str) -> StylePreset:
    if style_id not in PRESETS:
        raise KeyError(f"unknown style {style_id}; choose from {list(PRESETS)}")
    return PRESETS[style_id]


def load_lock() -> dict[str, Any] | None:
    if not LOCK_PATH.exists():
        return None
    try:
        return json.loads(LOCK_PATH.read_text())
    except json.JSONDecodeError:
        return None


def save_lock(payload: dict[str, Any]) -> Path:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCK_PATH.write_text(json.dumps(payload, indent=2))
    return LOCK_PATH


def active_style() -> StylePreset:
    lock = load_lock()
    if lock and lock.get("winner_style_id") in PRESETS:
        return PRESETS[lock["winner_style_id"]]
    return PRESETS["korean_manhwa"]


def build_prompt_for(
    style: StylePreset,
    scene: str,
    *,
    characters: str | None = None,
    negative: bool = False,
) -> str:
    parts = [scene.strip()]
    if characters:
        parts.append(f"Characters: {characters.strip()}")
    parts.append(style.suffix)
    text = ". ".join(parts)
    if negative:
        text = f"{text}. Avoid: {style.negative}"
    return text
