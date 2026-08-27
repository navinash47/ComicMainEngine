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

## G1 — Eval harness (prove-shot)

- `46eb043` phase-v2b-g1: pairwise eval harness and preference log on HIMYM p1
- Four-axis scorecard on locked B3 (mean SSIM(depth) 0.584, floor 0.53). Identity is cheap `grid_hist_8x8` vs beauty, log-only until B4 faces exist.
- Pairwise Gemini `gemini-3.6-flash` (direct `GOOGLE_API_KEY`; `gemini-2.5-flash` 404). 12 catalog pairs + BoN knockout, A/B swap. 46 ok calls, $0.043. Never OmniRoute images.
- 12/12 human labels on `/v2b/gate1`. Exact LLM–human 4/12; tie-lenient 10/12. Two hard disagreements: `b_b2_beauty` and `c_b2_beauty` (human prefers beauty, Gemini prefers B2). Harness PASS; exact 8/12 is calibration debt, not an RL train signal.
- BoN seeds `{42,43,44,45}` on existing AOVs. Winners: cam_a seed_44, cam_b seed_44, cam_c seed_42 (identical to locked B3). Human+Gemini both pick locked B3 over cam_b BoN.
- Log: `data/v2b/eval/preferences.jsonl`. Scorecard: `data/v2b/eval/himym_ep01_g1_scorecard.json`. B8 stays locked. No DPO/PPO/GRPO trained.
- Run: `PYTHONPATH=src python scripts/v2b_gate1.py --score --agreement`

## B4 — Character LoRA (Dad)

- `6472480` phase-v2b-b4: bootstrap character LoRA from stylized 3D turntable
- Block humanoids replace capsules. G1 `cam_{a,b,c}` frozen; B4 writes `outputs/v2b/himym_ep01/b4/`.
- Dad standing turntable `--quick` 8 views × 2 seeds (denoise 0.40, depth CN 0.55, lineart 0.45). 4 Maya contrast views, no Maya LoRA.
- SD 1.5 LoRA trained in `ComfyUI/.venv` (diffusers+PEFT, rank 16, 250 steps). SHA256 `bfd7f7d8023ba91bbf47b420a11a128465ac620865ea8a8ef6a1d973d153bfaf`. Weights gitignored. Trigger `ce_dad_rohan`.
- Stacked style+Dad LoRA on living-room cameras. Scorecard `data/v2b/eval/himym_ep01_b4.json`: mean SSIM(depth) 0.5488 (floor 0.53); restage MAE ≤ 0.082; DINOv2-small 3/4 Dad>Maya. `grid_hist_8x8` log-only.
- B8 stays locked. No InstantID/IP-Adapter. No DPO.
- Run: `PYTHONPATH=src python scripts/v2b_b4.py --all --quick`

## B5–B9

Locked until each phase starts.
