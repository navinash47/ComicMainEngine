"""Img2img stylize over ComfyUI HTTP. Local ComfyUI only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from comicengine.config import ROOT
from comicengine.v2b.comfy import client

WORKFLOW = Path(__file__).resolve().parent / "workflows" / "img2img_sd15.json"
CONTROLNET_WORKFLOW = Path(__file__).resolve().parent / "workflows" / "img2img_controlnet_sd15.json"
DEFAULT_CKPT = "v1-5-pruned-emaonly.safetensors"
SEED = 42
DEPTH_CN = "control_v11f1p_sd15_depth.pth"
LINEART_CN = "control_v11p_sd15_lineart.pth"
CONTROLNET_DIR = ROOT / "ComfyUI" / "models" / "controlnet"


def controlnet_weights_exist() -> bool:
    return (CONTROLNET_DIR / DEPTH_CN).is_file() and (CONTROLNET_DIR / LINEART_CN).is_file()


def _workflow(image_name: str, ckpt: str, seed: int) -> dict[str, Any]:
    data = json.loads(WORKFLOW.read_text())
    data["10"]["inputs"]["image"] = image_name
    data["4"]["inputs"]["ckpt_name"] = ckpt
    data["3"]["inputs"]["seed"] = seed
    return data


def _controlnet_workflow(
    beauty_name: str,
    depth_name: str,
    lineart_name: str,
    ckpt: str,
    seed: int,
) -> dict[str, Any]:
    data = json.loads(CONTROLNET_WORKFLOW.read_text())
    data["10"]["inputs"]["image"] = beauty_name
    data["12"]["inputs"]["image"] = depth_name
    data["13"]["inputs"]["image"] = lineart_name
    data["4"]["inputs"]["ckpt_name"] = ckpt
    data["3"]["inputs"]["seed"] = seed
    data["14"]["inputs"]["control_net_name"] = DEPTH_CN
    data["15"]["inputs"]["control_net_name"] = LINEART_CN
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


def stylize_controlnet(
    beauty_png: Path,
    depth_png: Path,
    lineart_png: Path,
    dest_png: Path,
    *,
    base: str = client.DEFAULT_BASE,
    ckpt: str = DEFAULT_CKPT,
    seed: int = SEED,
) -> Path:
    if not controlnet_weights_exist():
        raise FileNotFoundError(
            "Missing SD 1.5 ControlNet weights in ComfyUI/models/controlnet/: "
            f"{DEPTH_CN} and {LINEART_CN}"
        )
    client.wait_until_up(base)
    beauty_name = client.upload_image(Path(beauty_png), base=base)
    depth_name = client.upload_image(Path(depth_png), base=base)
    lineart_name = client.upload_image(Path(lineart_png), base=base)
    prompt_id = client.queue_prompt(
        _controlnet_workflow(beauty_name, depth_name, lineart_name, ckpt, seed),
        base=base,
    )
    history = client.wait_history(prompt_id, base=base)
    return client.fetch_first_image(history, Path(dest_png), base=base)
