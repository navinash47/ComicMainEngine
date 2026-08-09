"""Active style helpers — prefer baked-off lock / STYLE_ID env, else Korean manhwa."""

from __future__ import annotations

import os

from comicengine.styles import PRESETS, active_style as _active_from_lock
from comicengine.styles import build_prompt_for, get_preset, load_lock


def active_style():
    env_id = (os.getenv("STYLE_ID") or "").strip()
    if env_id in PRESETS:
        return PRESETS[env_id]
    lock = load_lock()
    if lock and lock.get("human_judge_pending"):
        # User is comparing finals; default to Korean manhwa unless STYLE_ID set
        preferred = lock.get("preferred_while_judging") or "korean_manhwa"
        if preferred in PRESETS:
            return PRESETS[preferred]
    return _active_from_lock()


_style = active_style()
STYLE_NAME = _style.id
STYLE_SUFFIX = _style.suffix
NEGATIVE_PROMPT = _style.negative


def build_prompt(scene: str, *, characters: str | None = None, negative: bool = False) -> str:
    return build_prompt_for(active_style(), scene, characters=characters, negative=negative)
