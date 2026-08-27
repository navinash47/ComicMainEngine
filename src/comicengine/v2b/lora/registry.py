"""Pinned style LoRA metadata. Weights are gitignored; only the hash is tracked."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from comicengine.config import ROOT

REGISTRY_PATH = ROOT / "data" / "v2b" / "lora" / "registry.json"
LORA_DIR = ROOT / "ComfyUI" / "models" / "loras"


class StyleLoraError(RuntimeError):
    pass


def load_style() -> dict[str, Any]:
    data = json.loads(REGISTRY_PATH.read_text())
    style = data.get("style")
    if not isinstance(style, dict) or not style.get("filename"):
        raise StyleLoraError(f"missing style entry in {REGISTRY_PATH}")
    return style


def style_lora_path(style: dict[str, Any] | None = None) -> Path:
    style = style or load_style()
    return LORA_DIR / str(style["filename"])


def style_lora_exists(style: dict[str, Any] | None = None) -> bool:
    return style_lora_path(style).is_file()


def verify_style_lora(style: dict[str, Any] | None = None) -> Path:
    style = style or load_style()
    path = style_lora_path(style)
    if not path.is_file():
        raise StyleLoraError(
            f"Missing style LoRA at {path}. Run scripts/v2b_setup_local.sh "
            f"(source: {style.get('source_url')})"
        )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    expected = str(style.get("sha256") or "").lower()
    if expected and digest != expected:
        raise StyleLoraError(
            f"Style LoRA hash mismatch for {path.name}: got {digest}, expected {expected}"
        )
    return path
