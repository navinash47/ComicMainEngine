# Version 2B — 3D-previs comic pipeline

Readable without running Blender or ComfyUI. Program state lives in [`data/v2b_program.json`](../data/v2b_program.json). One commit per phase gate. Branches: `phase-v2b-b0` … `phase-v2b-g1` … `phase-v2b-b9`.

**Dashboard:** local admin → **Version 2B** → [`/v2b`](http://127.0.0.1:8770/v2b) (ComicEngine is on **8770**; 8765 is Procedural City). Gate 1 pairwise: [`/v2b/gate1`](http://127.0.0.1:8770/v2b/gate1). Architecture diagrams are on that page (`#architecture`). Raw markdown: [`/v2b/architecture`](http://127.0.0.1:8770/v2b/architecture). Source research plan: [`/v2b/source-plan`](http://127.0.0.1:8770/v2b/source-plan). API: `/api/v2b/program`. This is a live view of the JSON — it does not replace Version 2 or Version 2A.

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

Never route Nano Banana / Flux / GPT-Image / SDXL / ComfyUI traffic through OmniRoute. Gemini text hellos stay direct Google. Image generation in 2B is local ComfyUI (SD 1.5 + ControlNet + style LoRA on this Mac; SDXL is the later ship stack) unless a later phase explicitly uses a direct API for dataset stylize.

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
- **ComfyUI** persistent local server at `localhost:8188` (repo-local `ComfyUI/`, gitignored). **B2–B4 use SD 1.5 ControlNet + LoRA on MPS**; SDXL is the later ship stack, not this machine. Workflows stored as API-format JSON. One instance per GPU; no concurrent `/prompt`s.
- **SDXL** base (OpenRAIL++-M, commercial OK) + richest ControlNet/LoRA ecosystem on 16GB — ship target when ControlNet fits. This Mac locks SD 1.5. FLUX.1-dev is non-commercial — do not ship on it.
- **Character LoRA (B4):** diffusers + PEFT in `ComfyUI/.venv` (torch/MPS). Compass named kohya/SDXL; kohya-on-MPS is a time sink and SDXL+ControlNet does not fit. Style LoRA for B3 was acquired, not trained. Do not add torch to ComicEngine `.venv`.
- **Eval:** `grid_hist_8x8` is log-only. B4 identity is DINOv2-small in `ComfyUI/.venv` (Dad holdout vs Dad sheet vs Maya), Gemini `same_person` fallback. B5 location is DINOv2-small on character-painted backgrounds; gate is same-room mean > cross-room (Compass 0.9 is a hypothesis). SSIM(depth) structure floor 0.53 is the living-room calibration, not empty lobby. Luminance hist + key-light side; Gemini Flash **pairwise** (not 1–10 scores). Compass named Qwen3-VL; G1 used `gemini-3.6-flash` direct `GOOGLE_API_KEY`. Never OmniRoute images.
- **Determinism:** pin seeds, sampler, steps, CFG, model/LoRA hashes. Content-hash cache skips unchanged specs.

### Intended package (B1+, not this freeze)

```
src/comicengine/v2b/
  blender/   # spec → bpy, AOVs, headless wrapper
  comfy/     # HTTP client + workflow JSON
  lora/      # registry + turntable bootstrap (train script: scripts/v2b_b4_train.py)
  eval/      # DINOv2 (ComfyUI venv), structure, VLM pairwise
  pipeline/  # panel + storyboard orchestration
data/v2b/    # specs, later assets (git-lfs/DVC)
```

Do not put 2B pipeline code into `panel_batch.py`, `script_engine.py`, or 2A modules.

---

## Layers

### Layer 1 — Spec → headless Blender

A panel spec names location, character(s), camera, lights, seed. **B5** loads versioned JSON under `data/v2b/specs/` (Pydantic in `src/comicengine/v2b/spec.py`; not `episode_schema.py`). Headless `build_scene.py` places primitives from that JSON. `himym_p1.py` stays the frozen B1–B4 living-room path. AOVs: beauty, normalized Z depth (near=white), Grease Pencil Line Art, normal, object-index (dad=R, maya=G). Run via `blender --background --factory-startup --python build_scene.py`. Re-run with the same spec+seed must be byte-identical or near-identical on the 3D render.

### Layer 2 — ComfyUI stylize

**B3 locks an SD 1.5 style LoRA on MPS; SDXL later.** POST a parametrized API workflow: img2img from the beauty pass, ControlNet-depth + ControlNet-lineart (strengths 0.75 / 0.65 on panels; B4 bootstrap uses 0.55 / 0.45), then `LoraLoader` at a locked weight. Checkpoint `v1-5-pruned-emaonly`, euler 18, CFG 6.5, seed 42, denoise 0.65 on panels (0.40 on the character bootstrap). Style registry: [`data/v2b/lora/registry.json`](../data/v2b/lora/registry.json) (hash only; weights gitignored). B4 stacks a second Dad `LoraLoader`. Character LoRAs gated by object-index masks (B6). Retrieve PNGs via `/history` + `/view`. Never OmniRoute.

### Layer 3 — Identity from the 3D model (B4)

Capsules cannot be the dataset (a LoRA of blobs stays blobs). B4 replaces them with **block humanoids** (Dad: sweater + curly hair spheres; Maya: hoodie + ponytail) and writes AOVs under `outputs/v2b/himym_ep01/b4/` so G1 `cam_{a,b,c}` stays frozen.

1. Standing Dad turntable (no sofa): 12 azimuths × 2 elevations, or `--quick` 8 views. Optional 4 Maya standing views as a contrast set, not a Maya LoRA.
2. Stylize with the locked B3 style LoRA but **weaker** ControlNet: denoise **0.40**, depth 0.55, lineart 0.45, seeds `{42,43}`, trigger `ce_dad_rohan`.
3. Train **SD 1.5** rank-16 LoRA in `ComfyUI/.venv` (diffusers+PEFT). Weights gitignored; SHA256 in `data/v2b/lora/registry.json` `characters.dad`.
4. Infer panel 1 with stacked `LoraLoader`s (style then Dad at ~0.8) on the **new** living-room AOVs.
5. Eval: mean SSIM(depth) ≥ 0.53 vs **B4** depth; restage MAE vs beauty ≤ 0.12; identity Dad holdout closer to Dad sheet than Maya on ≥6/8 (DINOv2) or Gemini fallback. `grid_hist_8x8` stays log-only. Do not claim Compass 0.85.

B6 is when two LoRAs get object-index masks. IP-Adapter / InstantID / PuLID stay fallbacks (InsightFace terms + photoreal bias).

### Layer 3.5 — Location reuse (B5)

Versioned location JSON (`data/v2b/specs/locations/`) + panel runfile (`himym_ep01_b5.json`). Prove: living room ×3 (stacked style+Dad LoRA) and Grand Oriole lobby ×2 (style only, empty — no Rohan LoRA). Location eval: character-index painted out, DINOv2-small on backgrounds; gate is **same-room mean > cross-room**. Compass 0.9 is a hypothesis. Structure floor 0.53 is the living-room calibration, not empty lobby. Writes `outputs/v2b/himym_ep01/b5/`. G1/B4 trees stay frozen.

### Layer 4 — Eval + best-of-N (G1 prove-shot; B8 later)

G1 ran the four-axis scorecard + pairwise VLM + N=4 seed BoN on HIMYM panel 1 (3 cameras). Hard gate is **mean** SSIM(depth) ≥ 0.53 (cam_b is often just under per-camera). Identity is log-only until B4. Preferences land in `data/v2b/eval/preferences.jsonl` for later B9. B8 is the same harness on more locations — do not mark B8 complete from G1. Diffusion-DPO (B9) is optional and cloud-only.

---

## Test series — HIMYM Episode 1 (not the 2A Capture series)

2B proves the pipeline on the **longest V1 episode**, not a nameless cube and not Aranya.

- **Series:** How I Met Your Mother — Episode 1: Infatuation (`himym_ep01`)
- **Length:** 76 panels (V1 `panel_count` 76 / 76 ok)
- **Leads:** Dad (Rohan present), Maya, Young Rohan, Elena
- **Packet:** `data/v2b/episodes/ep01.json` (2B-owned). V1 phase4 JSON is the read-only source.
- **B1 prove shot — panel 1 only:** living-room sofa at night, soft lamp. Dad sits beside Maya — no book — knees almost touching. Low-detail room + two seated primitives. Camera and key light locked in the spec. Output: `outputs/v2b/himym_ep01/panel_01.png`.
- **B2 cameras:** `outputs/v2b/himym_ep01/cam_{a,b,c}/` (hero two-shot, closer, slight profile). Depth + GP lineart drive SD 1.5 ControlNet.
- **B3 style:** same three cameras, locked `storybook_anime_lora` at strength 1.0. Gut-check is these framings, not 10 scenes (B8).
- **G1 eval:** 12 human A/B labels on `/v2b/gate1`; Gemini pairwise with A/B swap; BoN seeds 42–45. Scorecard `data/v2b/eval/himym_ep01_g1_scorecard.json`.
- **B4 character:** block meshes + Dad SD 1.5 LoRA. Scorecard `data/v2b/eval/himym_ep01_b4.json`. Maya LoRA waits for B6. Do not InstantID.
- **B5 locations:** spec-driven `living_room` ×3 + `grand_oriole_lobby` ×2. Scorecard `data/v2b/eval/himym_ep01_b5.json`. No Rohan/Elena LoRA. Do not InstantID.
- **Later:** B6 is two LoRAs + object-index masks. B7 may sequence more of the 76. Do not render all 76 in B1.

---

## IP and licensing (short)

- SDXL: CreativeML OpenRAIL++-M — commercial OK. Primary ship base.
- FLUX.1-dev: non-commercial — avoid for a sellable product.
- Train style/character LoRAs on our own or licensed art. B3 acquired `neonforestmist/sd15-storybook-anime-lora` (CreativeML OpenRAIL-M); SHA256 in `data/v2b/lora/registry.json`. Do not commit the `.safetensors`.
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
| **G1** | Phase 7 eval (prove-shot) | Pairwise harness | Four-axis scorecard + 12 human A/B + Gemini pairwise + BoN N=4; no DPO | `phase-v2b-g1: pairwise eval harness and preference log on HIMYM p1` |
| **B4** | Phase 3 character LoRA | Identity from 3D | Block humanoids; SD 1.5 Dad LoRA from stylized turntable; held-out Dad>Maya; mean SSIM ≥ 0.53 | `phase-v2b-b4: bootstrap character LoRA from stylized 3D turntable` |
| **B5** | Phase 4 location reuse | Spec-driven panels | Versioned 3D locations; four-axis scorecard per panel | `phase-v2b-b5: spec-driven locations with four-axis scorecards` |
| **B6** | Phase 5 multi-character | No identity bleed | Two+ LoRAs gated by object-index masks | `phase-v2b-b6: mask-driven multi-character LoRAs without bleed` |
| **B7** | Phase 6 sequencing | Storyboard run | Ordered panels, cache hits skip unchanged renders | `phase-v2b-b7: multi-panel storyboard sequencing with cache` |
| **B8** | Phase 7 best-of-N | Auto-select | N candidates, threshold+rank, human agreement floor on a labeled set | `phase-v2b-b8: pairwise VLM best-of-N panel selection` |
| **B9** | Phase 8 RL (optional) | Later, maybe | Cloud Diffusion-DPO only after preference pairs exist | `phase-v2b-b9: optional cloud DPO from 2B preference pairs` |

B0–B5 and G1 are complete. B6–B9 stay `locked` in `v2b_program.json` until that phase starts. B9 stays optional.

## Non-goals for B0

- No Blender scripts, no ComfyUI client, no LoRA trainer, no `src/comicengine/v2b/` package yet.
- No edits to 2A episode JSON, 2A program, Version 2 program, or `episode_schema.py`.
