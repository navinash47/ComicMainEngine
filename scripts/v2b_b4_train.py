#!/usr/bin/env python3
"""Train SD 1.5 Dad LoRA. Must run with ComfyUI/.venv (torch/MPS). Never OmniRoute."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "data" / "v2b" / "lora" / "dad" / "metadata.json"
CKPT = ROOT / "ComfyUI" / "models" / "checkpoints" / "v1-5-pruned-emaonly.safetensors"
OUT = ROOT / "ComfyUI" / "models" / "loras" / "ce_dad_rohan.safetensors"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=800)
    parser.add_argument("--rank", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--meta", default=str(META))
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args()

    import gc

    import numpy as np
    import torch
    from diffusers import AutoencoderKL, DDPMScheduler, StableDiffusionPipeline
    from diffusers.utils import convert_state_dict_to_kohya
    from peft import LoraConfig, get_peft_model
    from peft.utils import get_peft_model_state_dict
    from PIL import Image
    from safetensors.torch import save_file
    from transformers import CLIPTextModel, CLIPTokenizer

    meta_path = Path(args.meta)
    if not meta_path.is_file():
        raise SystemExit(f"missing {meta_path}; run bootstrap first")
    if not CKPT.is_file():
        raise SystemExit(f"missing checkpoint {CKPT}")
    meta = json.loads(meta_path.read_text())
    rows = list(meta.get("train") or [])
    if len(rows) < 4:
        raise SystemExit(f"need at least 4 train images, got {len(rows)}")

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    dtype = torch.float32

    pipe = StableDiffusionPipeline.from_single_file(str(CKPT), torch_dtype=dtype, local_files_only=False)
    tokenizer: CLIPTokenizer = pipe.tokenizer
    text_encoder: CLIPTextModel = pipe.text_encoder.to(device)
    vae: AutoencoderKL = pipe.vae.to(device)
    unet = pipe.unet.to(device)
    noise_sched = DDPMScheduler.from_config(pipe.scheduler.config)
    del pipe
    gc.collect()
    vae.requires_grad_(False)
    text_encoder.requires_grad_(False)
    unet.requires_grad_(False)
    lora = LoraConfig(
        r=args.rank,
        lora_alpha=args.rank,
        init_lora_weights="gaussian",
        target_modules=["to_k", "to_q", "to_v", "to_out.0"],
    )
    unet = get_peft_model(unet, lora)
    unet.train()
    if hasattr(unet, "enable_gradient_checkpointing"):
        unet.enable_gradient_checkpointing()

    cached: list[tuple[torch.Tensor, torch.Tensor]] = []
    with torch.no_grad():
        for row in rows:
            im = Image.open(row["png"]).convert("RGB").resize((512, 768), Image.Resampling.LANCZOS)
            pixel = torch.from_numpy((np.asarray(im).astype("float32") / 127.5) - 1.0).permute(2, 0, 1)
            pixel = pixel.unsqueeze(0).to(device)
            latents = vae.encode(pixel).latent_dist.sample() * vae.config.scaling_factor
            tokens = tokenizer(
                [row["caption"]],
                padding="max_length",
                truncation=True,
                max_length=tokenizer.model_max_length,
                return_tensors="pt",
            ).input_ids.to(device)
            cond = text_encoder(tokens)[0]
            cached.append((latents.detach().cpu(), cond.detach().cpu()))
            print(f"cached {Path(row['png']).name}", flush=True)
    del vae, text_encoder
    gc.collect()
    if device.type == "mps":
        torch.mps.empty_cache()

    params = [p for p in unet.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=args.lr)
    step = 0
    order = list(range(len(cached)))
    while step < args.steps:
        if step % len(cached) == 0:
            rng = np.random.default_rng(step)
            rng.shuffle(order)
        latents, cond = cached[order[step % len(cached)]]
        latents = latents.to(device)
        cond = cond.to(device)
        noise = torch.randn_like(latents)
        t = torch.randint(0, noise_sched.config.num_train_timesteps, (latents.shape[0],), device=device)
        noisy = noise_sched.add_noise(latents, noise, t)
        pred = unet(noisy, t, encoder_hidden_states=cond).sample
        loss = torch.nn.functional.mse_loss(pred, noise)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        step += 1
        if step <= 5 or step % 25 == 0:
            print(f"step {step}/{args.steps} loss={float(loss.detach()):.4f}", flush=True)
        del pred, loss, noisy, noise, latents, cond

    state = get_peft_model_state_dict(unet)
    prefixed = {}
    for key, value in state.items():
        key = key.replace("base_model.model.", "")
        if not key.startswith("unet."):
            key = "unet." + key
        prefixed[key] = value
    kohya = convert_state_dict_to_kohya(prefixed)
    if not any("lora_unet" in k for k in kohya):
        raise RuntimeError(f"LoRA export missing lora_unet keys; sample={list(kohya)[:8]}")
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    cpu = {k: v.detach().to("cpu") for k, v in kohya.items()}
    save_file(cpu, str(dest))
    print(json.dumps({"out": str(dest), "steps": args.steps, "n_train": len(rows), "bytes": dest.stat().st_size}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ModuleNotFoundError as exc:
        print(f"missing package in this interpreter: {exc}", file=sys.stderr)
        print("Install into ComfyUI/.venv: pip install diffusers peft accelerate safetensors", file=sys.stderr)
        raise SystemExit(2)
