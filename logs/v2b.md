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

- `phase-v2b-b2: Blender AOVs drive multi-ControlNet structure`
- Three cameras under `outputs/v2b/himym_ep01/cam_{a,b,c}/`. Lineart is Grease Pencil Line Art (Blender 5.2 Freestyle-as-pass empty).
- SD 1.5 multi-ControlNet on MPS (depth 0.75, lineart 0.65, denoise 0.45). SDXL waits for B3+.
- Scorecard `data/v2b/eval/himym_ep01_b2_structure.json`: mean SSIM(depth) 0.575 (cheap skimage; hypothesis 0.7 calibrated to 0.53); mean edge IoU 0.368. Visual geometry lock holds.
- Run: `PYTHONPATH=src python scripts/v2b_panel.py`

## B3–B9

Locked until each phase starts.
