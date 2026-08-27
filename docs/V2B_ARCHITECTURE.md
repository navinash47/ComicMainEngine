# Version 2B — 3D-previs comic pipeline

Readable without running Blender or ComfyUI. Program state lives in [`data/v2b_program.json`](../data/v2b_program.json). One commit per phase gate. Branches: `phase-v2b-b0` … `phase-v2b-b9`.

**Dashboard:** local admin → **Version 2B** → [`/v2b`](http://127.0.0.1:8770/v2b) (ComicEngine is on **8770**; 8765 is Procedural City). Architecture diagrams are on that page (`#architecture`). Raw markdown: [`/v2b/architecture`](http://127.0.0.1:8770/v2b/architecture). Source research plan: [`/v2b/source-plan`](http://127.0.0.1:8770/v2b/source-plan). API: `/api/v2b/program`. This is a live view of the JSON — it does not replace Version 2 or Version 2A.

External research (citation, not code): [`docs/V2B_SOURCE_PLAN.md`](V2B_SOURCE_PLAN.md) (Compass artifact). This file is the living contract for ComicMainEngine.

## Version 2 and Version 2A stay separate

**Version 2** (`data/v2_program.json`, phases 12–20: feedback harvest → sync → incident ledger → mistake-memory → product waves → knowledge graph → critic/DPO) is a **separate, frozen track**. Do not edit `data/v2_program.json` from 2B work.

**Version 2A** (`data/v2a_program.json`, phases A0–A5: you draw the shot; AI fills under locks) is a **separate, parallel track**. Do not edit `data/v2a_program.json`, `data/v2a/`, `docs/V2A_ARCHITECTURE.md`, or live `episode_schema.py` from 2B work. Do not rewrite 2A phases to become 3D-previs. 2B does **not** reuse the Aranya Capture episode packets.

**2B fixture:** V1 **How I Met Your Mother — Episode 1: Infatuation** (76 panels, longest existing script). The 2B-owned packet is [`data/v2b/episodes/ep01.json`](../data/v2b/episodes/ep01.json). Treat [`outputs/phase4/episode_how_i_met_your_mother_ep1.json`](../outputs/phase4/episode_how_i_met_your_mother_ep1.json) as **read-only** — do not edit it from 2B work.

| Track | What it owns | Image path |
|---|---|---|
| Version 2 | Reader feedback → product learning (text) | Existing V1 reader panels |
| Version 2A | Human sketch = camera | Sketch + locks → Gemini/fal enhance |
| Version 2B | 3D spec = camera | Headless Blender AOVs → local ComfyUI ControlNet |

2B is a **parallel program** with its own JSON, docs, dashboard, and branches.

---

**Idea:** camera, room, and blocking come from a versioned 3D spec rendered headless in Blender. Stylization is a ComfyUI img2img + multi-ControlNet graph you own. Character identity is a LoRA bootstrapped from stylized turntable renders of that 3D model. The defensible loop is orchestration + automated multi-axis best-of-N selection, not any single model.

**Honest limit:** LLM spatial reasoning is weak. Do not drive production scenes through live Blender MCP. MCP is a scratchpad to discover bpy calls; production is parametric scripts + JSON/YAML specs. Style-robust identity metrics (DINOv2/CLIP), not ArcFace on comic faces. RL/DPO on diffusion is later and needs cloud GPUs.

---

## Routing (do not invert)

| Traffic | Where | Keys / process |
|---|---|---|
| Text / scripts / captions (if any) | **OmniRoute** `localhost:20128` (`USE_OMNIROUTE=1`) | `OMNIROUTE_API_KEY` |
| Blender renders / AOVs | **Local subprocess** `blender --background --python` | Blender 5.2.1 LTS (`/opt/homebrew/bin/blender`) |
| Stylize / ControlNet / LoRA infer | **Local ComfyUI** HTTP `/prompt` + `/ws` | `localhost:8188` — never OmniRoute |
| Optional bootstrap stylize (B4) | **Direct provider APIs** | `GOOGLE_API_KEY`, fal from project `.env` |

Never route Nano Banana / Flux / GPT-Image / SDXL / ComfyUI traffic through OmniRoute. Gemini text hellos stay direct Google. Image generation in 2B is local ComfyUI (SDXL workhorse) unless a later phase explicitly uses a direct API for dataset stylize.

---

## How 2B differs from 2A and from today

Today (Version 1) and Version 2A still **do not pin geometry in 3D**:

```
V1:  StorySpec → art_prompt guesses pose → gemini_ref / Kontext → panel PNG
2A:  your sketch + four locks → enhance → panel PNG
```

Version 2B inverts the camera step again: **the 3D spec is the composition contract**.

```
panel spec (JSON/YAML)
  → headless bpy builds the scene
  → Cycles beauty + depth + normal + Freestyle + object-index
  → ComfyUI img2img + multi-ControlNet + style LoRA (+ character LoRA later)
  → eval scorecard (structure, identity, location, lighting)
  → best-of-N select
```

Skip StableGen. It textures 3D meshes; 2B needs flat stylized 2D panels.

---

## Stack (locked for B1+)

- **Python 3.11**, package under `src/comicengine/v2b/` (create in B1, not B0).
- **Blender** invoked headless. Homebrew currently installs **5.2.1 LTS** (`/opt/homebrew/bin/blender`). Compass suggested 4.2 for addons we are not using; do not install Blender MCP into the pipeline.
- **ComfyUI** persistent local server at `localhost:8188` (repo-local `ComfyUI/`, gitignored). **B2 uses SD 1.5 ControlNet on MPS**; SDXL is the later ship stack (B3+), not this gate. Workflows stored as API-format JSON. One instance per GPU; no concurrent `/prompt`s.
- **SDXL** base (OpenRAIL++-M, commercial OK) + richest ControlNet/LoRA ecosystem on 16GB. FLUX.1-dev is non-commercial — do not ship on it. Optional later: FLUX.1-schnell or Qwen-Image (Apache 2.0).
- **kohya_ss / sd-scripts** for SDXL LoRAs (B3–B4).
- **Eval:** DINOv2/CLIP identity; SSIM/LPIPS + depth/edge re-extract for structure; Qwen3-VL **pairwise** (not 1–10 scores) for lighting/aesthetic.
- **Determinism:** pin seeds, sampler, steps, CFG, model/LoRA hashes. Content-hash cache skips unchanged specs.

### Intended package (B1+, not this freeze)

```
src/comicengine/v2b/
  blender/   # spec → bpy, AOVs, headless wrapper
  comfy/     # HTTP client + workflow JSON
  lora/      # bootstrap + kohya (later)
  eval/      # DINOv2/CLIP, structure, VLM pairwise
  pipeline/  # panel + storyboard orchestration
data/v2b/    # specs, later assets (git-lfs/DVC)
```

Do not put 2B pipeline code into `panel_batch.py`, `script_engine.py`, or 2A modules.

---

## Layers

### Layer 1 — Spec → headless Blender

A panel spec names location, character(s), camera, lights, seed. Headless `himym_p1.py` emits beauty, normalized Z depth (near=white), Grease Pencil Line Art (Blender 5.2 Freestyle-as-pass is empty), normal, and object-index (dad=R, maya=G). Run via `blender --background --factory-startup --python himym_p1.py`. Fixed render settings. Re-run with the same spec+seed must be byte-identical or near-identical on the 3D render.

### Layer 2 — ComfyUI stylize

**B2 uses SD 1.5 ControlNet on MPS; SDXL later.** POST a parametrized API workflow: img2img from the beauty pass, ControlNet-depth + ControlNet-lineart (strengths ~0.55–0.8). Fixed checkpoint `v1-5-pruned-emaonly` + euler / seed 42. Style LoRA at a locked weight is B3 (SDXL). Character LoRAs gated by object-index masks (B6). Retrieve PNGs via `/history` + `/view`. Never OmniRoute.

### Layer 3 — Identity from the 3D model (B4)

1. Render the character turntable (many angles, poses, expressions, lights).
2. Stylize each render (img2img denoise ~0.4, ≥2 variants) so the LoRA learns identity, not the CG look.
3. Train SDXL LoRA (kohya). Held-out cameras for eval.

IP-Adapter / InstantID / PuLID are fallbacks only (InsightFace terms + photoreal bias).

### Layer 4 — Eval + best-of-N (B8)

N candidates per panel. Hard gates on structure and identity, then weighted rank + pairwise VLM. Scorecards are the preference dataset. Diffusion-DPO (B9) is optional and cloud-only.

---

## Test series — HIMYM Episode 1 (not the 2A Capture series)

2B proves the pipeline on the **longest V1 episode**, not a nameless cube and not Aranya.

- **Series:** How I Met Your Mother — Episode 1: Infatuation (`himym_ep01`)
- **Length:** 76 panels (V1 `panel_count` 76 / 76 ok)
- **Leads:** Dad (Rohan present), Maya, Young Rohan, Elena
- **Packet:** `data/v2b/episodes/ep01.json` (2B-owned). V1 phase4 JSON is the read-only source.
- **B1 prove shot — panel 1 only:** living-room sofa at night, soft lamp. Dad sits beside Maya — no book — knees almost touching. Low-detail room + two seated primitives. Camera and key light locked in the spec. Output: `outputs/v2b/himym_ep01/panel_01.png`.
- **B2 cameras:** `outputs/v2b/himym_ep01/cam_{a,b,c}/` (hero two-shot, closer, slight profile). Depth + GP lineart drive SD 1.5 ControlNet.
- **Later:** B5 reuses Grand Oriole / lobby / tram locations from the same packet. B7 may sequence more of the 76. Do not render all 76 in B1.

---

## IP and licensing (short)

- SDXL: CreativeML OpenRAIL++-M — commercial OK. Primary ship base.
- FLUX.1-dev: non-commercial — avoid for a sellable product.
- Train style/character LoRAs on our own or licensed art.
- Invoke Blender as an external subprocess; do not redistribute Blender or ship a GPL addon unless we accept GPL on that addon.
- InsightFace weights used by FaceID/InstantID/PuLID: non-commercial research terms — another reason LoRA-first.

---

## Phase gates (one commit each)

When a gate passes: commit on that phase branch, update the living report only if images/evals ran, merge to `master`. Do not batch two phases into one commit.

| Phase | Compass | Goal | Done when | Commit |
|---|---|---|---|---|
| **B0** | Architecture freeze | 2B is readable without Blender/ComfyUI | This doc + `data/v2b_program.json` + `/v2b`; Version 2 and 2A untouched | `phase-v2b-b0: freeze 3D-previs pipeline architecture beside Version 2 and 2A` |
| **B1** | Phase 0 vertical slice | Prove the chain | HIMYM ep1 **panel 1** living-room two-shot → Cycles → one ComfyUI PNG; same seed near-identical. Not all 76 panels. | `phase-v2b-b1: HIMYM ep1 panel 1 living-room two-shot through ComfyUI` |
| **B2** | Phase 1 AOVs + ControlNet | Geometry by construction | Depth + Freestyle consumed; `eval/structure` SSIM(depth) floor vs conditioning; 3 test cameras | `phase-v2b-b2: Blender AOVs drive multi-ControlNet structure` |
| **B3** | Phase 2 style LoRA | One comic style | Fixed style LoRA + locked checkpoint/sampler; style reads intentional across panels | `phase-v2b-b3: lock style LoRA on every 2B panel` |
| **B4** | Phase 3 character LoRA | Identity from 3D | Turntable → stylize → train; held-out DINOv2 identity; no baked-CG look | `phase-v2b-b4: bootstrap character LoRA from stylized 3D turntable` |
| **B5** | Phase 4 location reuse | Spec-driven panels | Versioned 3D locations; four-axis scorecard per panel | `phase-v2b-b5: spec-driven locations with four-axis scorecards` |
| **B6** | Phase 5 multi-character | No identity bleed | Two+ LoRAs gated by object-index masks | `phase-v2b-b6: mask-driven multi-character LoRAs without bleed` |
| **B7** | Phase 6 sequencing | Storyboard run | Ordered panels, cache hits skip unchanged renders | `phase-v2b-b7: multi-panel storyboard sequencing with cache` |
| **B8** | Phase 7 best-of-N | Auto-select | N candidates, threshold+rank, human agreement floor on a labeled set | `phase-v2b-b8: pairwise VLM best-of-N panel selection` |
| **B9** | Phase 8 RL (optional) | Later, maybe | Cloud Diffusion-DPO only after preference pairs exist | `phase-v2b-b9: optional cloud DPO from 2B preference pairs` |

B0, B1, and B2 are complete. B3–B9 stay `locked` in `v2b_program.json` until that phase starts. B9 stays optional.

## Non-goals for B0

- No Blender scripts, no ComfyUI client, no LoRA trainer, no `src/comicengine/v2b/` package yet.
- No edits to 2A episode JSON, 2A program, Version 2 program, or `episode_schema.py`.
