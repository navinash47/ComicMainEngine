"""Img2img stylize over ComfyUI HTTP. Local ComfyUI only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from comicengine.v2b.comfy import client

WORKFLOW = Path(__file__).resolve().parent / "workflows" / "img2img_sd15.json"
DEFAULT_CKPT = "v1-5-pruned-emaonly.safetensors"
SEED = 42


def _workflow(image_name: str, ckpt: str, seed: int) -> dict[str, Any]:
    data = json.loads(WORKFLOW.read_text())
    data["10"]["inputs"]["image"] = image_name
    data["4"]["inputs"]["ckpt_name"] = ckpt
    data["3"]["inputs"]["seed"] = seed
    return data


def stylize_img2img(
    beauty_png: Path,
    dest_png: Path,
    *,
    base: str = client.DEFAULT_BASE,
    ckpt: str = DEFAULT_CKPT,
    seed: int = SEED,
) -> Path:
    client.wait_until_up(base)
    uploaded = client.upload_image(Path(beauty_png), base=base)
    prompt_id = client.queue_prompt(_workflow(uploaded, ckpt, seed), base=base)
    history = client.wait_history(prompt_id, base=base)
    return client.fetch_first_image(history, Path(dest_png), base=base)
