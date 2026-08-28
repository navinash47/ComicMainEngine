"""Img2img stylize over ComfyUI HTTP. Local ComfyUI only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from comicengine.config import ROOT
from comicengine.v2b.comfy import client
from comicengine.v2b.lora.registry import load_style, style_lora_exists, verify_style_lora

WORKFLOW = Path(__file__).resolve().parent / "workflows" / "img2img_sd15.json"
CONTROLNET_WORKFLOW = Path(__file__).resolve().parent / "workflows" / "img2img_controlnet_sd15.json"
CONTROLNET_LORA_WORKFLOW = (
    Path(__file__).resolve().parent / "workflows" / "img2img_controlnet_lora_sd15.json"
)
INPAINT_LORA_WORKFLOW = (
    Path(__file__).resolve().parent / "workflows" / "img2img_controlnet_inpaint_lora_sd15.json"
)
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
    *,
    style_lora: bool = False,
    denoise: float | None = None,
    depth_strength: float | None = None,
    lineart_strength: float | None = None,
    positive: str | None = None,
    negative: str | None = None,
    character_lora: str | None = None,
    character_strength: float = 0.8,
) -> dict[str, Any]:
    use_style = style_lora or bool(character_lora)
    path = CONTROLNET_LORA_WORKFLOW if use_style else CONTROLNET_WORKFLOW
    data = json.loads(path.read_text())
    data["10"]["inputs"]["image"] = beauty_name
    data["12"]["inputs"]["image"] = depth_name
    data["13"]["inputs"]["image"] = lineart_name
    data["4"]["inputs"]["ckpt_name"] = ckpt
    data["3"]["inputs"]["seed"] = seed
    data["14"]["inputs"]["control_net_name"] = DEPTH_CN
    data["15"]["inputs"]["control_net_name"] = LINEART_CN
    if depth_strength is not None:
        data["16"]["inputs"]["strength"] = float(depth_strength)
    if lineart_strength is not None:
        data["17"]["inputs"]["strength"] = float(lineart_strength)
    if use_style:
        style = load_style()
        verify_style_lora(style)
        data["18"]["inputs"]["lora_name"] = style["filename"]
        data["18"]["inputs"]["strength_model"] = float(style["strength_model"])
        data["18"]["inputs"]["strength_clip"] = float(style["strength_clip"])
        data["6"]["inputs"]["text"] = positive or style["positive_prompt"]
        data["7"]["inputs"]["text"] = negative or style["negative_prompt"]
        data["3"]["inputs"]["cfg"] = float(style["cfg"])
        data["3"]["inputs"]["denoise"] = float(style["denoise"] if denoise is None else denoise)
        data["3"]["inputs"]["sampler_name"] = style["sampler_name"]
        data["3"]["inputs"]["scheduler"] = style["scheduler"]
        data["3"]["inputs"]["steps"] = int(style["steps"])
        data["4"]["inputs"]["ckpt_name"] = style.get("checkpoint") or ckpt
        data["3"]["inputs"]["seed"] = seed
    elif denoise is not None:
        data["3"]["inputs"]["denoise"] = float(denoise)
    if character_lora:
        if "18" not in data:
            raise RuntimeError("character LoRA requires the style-LoRA ControlNet graph")
        data["19"] = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": character_lora,
                "strength_model": float(character_strength),
                "strength_clip": float(character_strength),
                "model": ["18", 0],
                "clip": ["18", 1],
            },
        }
        data["3"]["inputs"]["model"] = ["19", 0]
        data["6"]["inputs"]["clip"] = ["19", 1]
        data["7"]["inputs"]["clip"] = ["19", 1]
    return data


def _inpaint_workflow(
    panel_name: str,
    depth_name: str,
    lineart_name: str,
    mask_name: str,
    ckpt: str,
    seed: int,
    *,
    character_lora: str,
    character_strength: float = 0.8,
    denoise: float | None = None,
    depth_strength: float | None = None,
    lineart_strength: float | None = None,
    positive: str | None = None,
    negative: str | None = None,
    grow_mask_by: int = 8,
) -> dict[str, Any]:
    style = load_style()
    verify_style_lora(style)
    data = json.loads(INPAINT_LORA_WORKFLOW.read_text())
    data["10"]["inputs"]["image"] = panel_name
    data["12"]["inputs"]["image"] = depth_name
    data["13"]["inputs"]["image"] = lineart_name
    data["19"]["inputs"]["image"] = mask_name
    data["4"]["inputs"]["ckpt_name"] = style.get("checkpoint") or ckpt
    data["3"]["inputs"]["seed"] = seed
    data["14"]["inputs"]["control_net_name"] = DEPTH_CN
    data["15"]["inputs"]["control_net_name"] = LINEART_CN
    data["18"]["inputs"]["lora_name"] = style["filename"]
    data["18"]["inputs"]["strength_model"] = float(style["strength_model"])
    data["18"]["inputs"]["strength_clip"] = float(style["strength_clip"])
    data["22"]["inputs"]["lora_name"] = character_lora
    data["22"]["inputs"]["strength_model"] = float(character_strength)
    data["22"]["inputs"]["strength_clip"] = float(character_strength)
    data["21"]["inputs"]["grow_mask_by"] = int(grow_mask_by)
    data["6"]["inputs"]["text"] = positive or data["6"]["inputs"]["text"]
    data["7"]["inputs"]["text"] = negative or style["negative_prompt"]
    data["3"]["inputs"]["cfg"] = float(style["cfg"])
    data["3"]["inputs"]["denoise"] = float(style["denoise"] if denoise is None else denoise)
    data["3"]["inputs"]["sampler_name"] = style["sampler_name"]
    data["3"]["inputs"]["scheduler"] = style["scheduler"]
    data["3"]["inputs"]["steps"] = int(style["steps"])
    if depth_strength is not None:
        data["16"]["inputs"]["strength"] = float(depth_strength)
    if lineart_strength is not None:
        data["17"]["inputs"]["strength"] = float(lineart_strength)
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
    style_lora: bool = False,
    denoise: float | None = None,
    depth_strength: float | None = None,
    lineart_strength: float | None = None,
    positive: str | None = None,
    negative: str | None = None,
    character_lora: str | None = None,
    character_strength: float = 0.8,
) -> Path:
    if not controlnet_weights_exist():
        raise FileNotFoundError(
            "Missing SD 1.5 ControlNet weights in ComfyUI/models/controlnet/: "
            f"{DEPTH_CN} and {LINEART_CN}"
        )
    if (style_lora or character_lora) and not style_lora_exists():
        verify_style_lora()
    client.wait_until_up(base)
    beauty_name = client.upload_image(Path(beauty_png), base=base)
    depth_name = client.upload_image(Path(depth_png), base=base)
    lineart_name = client.upload_image(Path(lineart_png), base=base)
    prompt_id = client.queue_prompt(
        _controlnet_workflow(
            beauty_name,
            depth_name,
            lineart_name,
            ckpt,
            seed,
            style_lora=style_lora,
            denoise=denoise,
            depth_strength=depth_strength,
            lineart_strength=lineart_strength,
            positive=positive,
            negative=negative,
            character_lora=character_lora,
            character_strength=character_strength,
        ),
        base=base,
    )
    history = client.wait_history(prompt_id, base=base)
    return client.fetch_first_image(history, Path(dest_png), base=base)


def stylize_inpaint_controlnet(
    panel_png: Path,
    depth_png: Path,
    lineart_png: Path,
    mask_png: Path,
    dest_png: Path,
    *,
    character_lora: str,
    character_strength: float = 0.8,
    base: str = client.DEFAULT_BASE,
    ckpt: str = DEFAULT_CKPT,
    seed: int = SEED,
    denoise: float | None = 0.55,
    depth_strength: float | None = None,
    lineart_strength: float | None = None,
    positive: str | None = None,
    negative: str | None = None,
    grow_mask_by: int = 8,
) -> Path:
    """Pass-2: denoise only the object-index mask. Style LoRA + one character LoRA."""
    if not controlnet_weights_exist():
        raise FileNotFoundError(
            "Missing SD 1.5 ControlNet weights in ComfyUI/models/controlnet/: "
            f"{DEPTH_CN} and {LINEART_CN}"
        )
    verify_style_lora()
    client.wait_until_up(base)
    panel_name = client.upload_image(Path(panel_png), base=base)
    depth_name = client.upload_image(Path(depth_png), base=base)
    lineart_name = client.upload_image(Path(lineart_png), base=base)
    mask_name = client.upload_image(Path(mask_png), base=base)
    prompt_id = client.queue_prompt(
        _inpaint_workflow(
            panel_name,
            depth_name,
            lineart_name,
            mask_name,
            ckpt,
            seed,
            character_lora=character_lora,
            character_strength=character_strength,
            denoise=denoise,
            depth_strength=depth_strength,
            lineart_strength=lineart_strength,
            positive=positive,
            negative=negative,
            grow_mask_by=grow_mask_by,
        ),
        base=base,
    )
    history = client.wait_history(prompt_id, base=base)
    return client.fetch_first_image(history, Path(dest_png), base=base)
