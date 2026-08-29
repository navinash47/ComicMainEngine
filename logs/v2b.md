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

## B5 — Location reuse

- `3b3cbdb` phase-v2b-b5: spec-driven locations with four-axis scorecards
- Versioned JSON under `data/v2b/specs/` (Pydantic). `build_scene.py` is spec-driven. `himym_p1.py` stays the frozen B1–B4 path.
- Prove: living room ×3 (style+Dad LoRA) + Grand Oriole lobby ×2 (style only, empty). No Rohan/Elena/Maya LoRA. Tram not in this gate.
- Scorecard `data/v2b/eval/himym_ep01_b5.json`: living mean SSIM(depth) 0.5489 (floor 0.53). Lobby mean 0.478 (empty-room cheap-depth). DINOv2 background living 0.825 vs living–lobby 0.476 (same-room beats cross-room). Compass 0.9 not claimed.
- Outputs `outputs/v2b/himym_ep01/b5/`. G1/B4 frozen. B8 stays locked.
- Run: `PYTHONPATH=src python scripts/v2b_b5.py --all`

## B6 — Multi-character masks

- `3e65840` phase-v2b-b6: mask-driven multi-character LoRAs without bleed
- Maya SD 1.5 LoRA from B4 standing turntable AOVs (`--quick` 8 views × 2 seeds, 12 train / 4 holdout). Rank 16, 250 steps in `ComfyUI/.venv`. SHA256 `b767153fc38dbf7aad445165868036e14d9a8fee60fe5f0ed7ef722f9b168d86`. Weights gitignored. Trigger `ce_maya`.
- Two-pass on living-room cam_a and cam_c: style+Dad globally, then `VAEEncodeForInpaint` on G-index with Maya LoRA. cam_b skipped. G1/B4/B5 frozen. Outputs `outputs/v2b/himym_ep01/b6/`.
- Scorecard `data/v2b/eval/himym_ep01_b6.json`: mean SSIM(depth) 0.5917 (floor 0.53). Maya holdout DINOv2 4/4. Bleed: Dad vs pass1 0.966 / 0.984; Maya G-crop own>cross. Seated dad_own vs Maya sheet is log-only (block two-shot). Compass 0.85 not claimed.
- No Rohan/Elena LoRA. No InstantID. B8 stays locked.
- Run: `PYTHONPATH=src python scripts/v2b_b6.py --all --quick`

## G2 — Licensed character meshes

- `phase-v2b-g2: licensed glTF characters replace block humanoids`
- Kenney Animated Characters Protagonists 1.1 (CC0). Stand-in cartoon skaters, not Indian-presenting Dad/Maya. LICENSE + registry under `data/v2b/meshes/`. Zip cache gitignored.
- New LoRAs (do not overwrite B4/B6): `ce_dad_gltf` SHA256 `7b71b79802d25fab7080e96b9f056fe3b6ea6e452f5fb4abaaf855b232bdf3c4`, `ce_maya_gltf` SHA256 `2681efe4c931c70c178ddef4cf2a2b6781a93ab9182b7397a345b5560c47ce57`. Rank 16, 250 steps `--quick`.
- Two-pass on living-room cam_a and cam_c. Sibling tree `outputs/v2b/himym_ep01/g2/`. G1/B4/B5/B6 frozen.
- Scorecard `data/v2b/eval/himym_ep01_g2.json`: mean SSIM(depth) 0.5808 (floor 0.53). cam_a 0.523 under per-camera. Maya holdout DINOv2 4/4. Bleed: Dad vs pass1 0.990 / 0.979; Maya G-crop own>cross. Seated dad_own vs Maya sheet log-only.
- Rollup `data/v2b/eval/himym_ep01_until_now.json` (B2–G2). G3 catalog search stays locked. No InstantID. B8 stays locked.
- Run: `PYTHONPATH=src python scripts/v2b_g2.py --all --quick`

## G3 — Character catalog search

Locked. Dashboard search → pick a licensed glTF → drop into the spec. User-requested; not this gate.

## B7–B9

Locked until each phase starts.
