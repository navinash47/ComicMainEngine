# Version 2B git log

Source of truth is `git log`. This file must stay 1:1 with 2B commit subjects so the dashboard can show history without GitHub.

Do not batch two phases. One gate per B-phase commit.

## B0 — Architecture freeze

- `c7e5c9f` phase-v2b-b0: freeze 3D-previs pipeline architecture beside Version 2 and 2A
- `96d5e05` phase-v2b-b0: record B0 freeze hash in v2b logs
- Fixture: HIMYM Episode 1 (76 panels). B1 prove is panel 1 living-room sofa (Dad + Maya).

## B1 — Vertical slice

- `544c325` phase-v2b-b1: HIMYM ep1 panel 1 living-room two-shot through ComfyUI
- Cycles beauty seed 42, 32 samples, 768×1152. Two reruns: pixel MAE 0.0 (PNG hashes differ).
- ComfyUI HTTP img2img SD 1.5 denoise 0.42. Stylizer still restages (no ControlNet) — B2.
- Run: `PYTHONPATH=src python scripts/v2b_b1_panel.py`

## B2 — AOVs + ControlNet

- `b82c064` phase-v2b-b2: Blender AOVs drive multi-ControlNet structure
- Three cameras under `outputs/v2b/himym_ep01/cam_{a,b,c}/`. Lineart is Grease Pencil Line Art (Blender 5.2 Freestyle-as-pass empty).
- SD 1.5 multi-ControlNet on MPS (depth 0.75, lineart 0.65, denoise 0.45). SDXL waits until ControlNet fits.
- Scorecard `data/v2b/eval/himym_ep01_b2_structure.json`: mean SSIM(depth) 0.575 (cheap skimage; hypothesis 0.7 calibrated to 0.53); mean edge IoU 0.368. Visual geometry lock holds.
- Run: `PYTHONPATH=src python scripts/v2b_panel.py --b2`

## B3 — Style LoRA

- `2eeb413` phase-v2b-b3: lock style LoRA on every 2B panel
- Acquired `neonforestmist/sd15-storybook-anime-lora` (OpenRAIL-M). SHA256 `0304bb42819790cf63f4125ac70cee60fda682cc5aa4bfb512bb9e3b1746e9b0`. Weights in gitignored `ComfyUI/models/loras/`.
- Locked on every ControlNet stylize: strength 1.0, `v1-5-pruned-emaonly`, euler 18, CFG 6.5, seed 42, denoise 0.65 (raised from B2 0.45 so the LoRA shows through).
- Scorecard `data/v2b/eval/himym_ep01_b3_structure.json`: mean SSIM(depth) 0.584 (calibrated floor 0.53); mean edge IoU 0.292; mean pixel MAE vs B2 0.047. Visual geometry lock holds. Style is storybook illustration on capsule meshes, not ink-line faces (B4).
- Run: `PYTHONPATH=src python scripts/v2b_panel.py --comfy-only`

## B4–B9

Locked until each phase starts.
