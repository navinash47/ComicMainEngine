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


def _load() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text())


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_style() -> dict[str, Any]:
    style = _load().get("style")
    if not isinstance(style, dict) or not style.get("filename"):
        raise StyleLoraError(f"missing style entry in {REGISTRY_PATH}")
    return style


def load_character(char_id: str = "dad") -> dict[str, Any]:
    block = (_load().get("characters") or {}).get(char_id)
    if not isinstance(block, dict) or not block.get("filename"):
        raise StyleLoraError(f"missing characters.{char_id} in {REGISTRY_PATH}")
    return block


def character_lora_path(char_id: str = "dad") -> Path:
    return LORA_DIR / str(load_character(char_id)["filename"])


def character_lora_exists(char_id: str = "dad") -> bool:
    try:
        return character_lora_path(char_id).is_file()
    except StyleLoraError:
        return False


def verify_character_lora(char_id: str = "dad") -> Path:
    spec = load_character(char_id)
    path = LORA_DIR / str(spec["filename"])
    if not path.is_file():
        raise StyleLoraError(f"Missing character LoRA at {path}")
    digest = sha256_file(path)
    expected = str(spec.get("sha256") or "").lower()
    if expected and digest != expected:
        raise StyleLoraError(f"Character LoRA hash mismatch for {path.name}: got {digest}, expected {expected}")
    return path


def upsert_character(char_id: str, **fields: Any) -> dict[str, Any]:
    data = _load()
    chars = dict(data.get("characters") or {})
    row = dict(chars.get(char_id) or {})
    row.update(fields)
    row["id"] = char_id
    chars[char_id] = row
    data["characters"] = chars
    REGISTRY_PATH.write_text(json.dumps(data, indent=2) + "\n")
    return row


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
