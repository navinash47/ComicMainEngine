# Storyboard-Driven Comic Generation Pipeline: Technical Build Plan & Evaluation

**Note on the referenced repo:** `github.com/navinash47/ComicMainEngine` is private and returned inaccessible, so this plan is built entirely from your architecture description, not from that code. Where I assume things about your current code, I flag it — reconcile this plan against your existing `ComicMainEngine` at the end.

## TL;DR
- **Build the pipeline code-first, not conversationally.** Have Cursor generate parametric Blender `bpy` scripts run headless (`blender --background --python`), NOT drive scene-blocking through Blender MCP live. MCP is genuinely mature for interactive exploration (`ahujasid/blender-mcp`: 26.3k stars, 2.5k forks, MIT, actively maintained) but is non-deterministic and un-versionable — fatal for a reproducible production pipeline. Use MCP only as a scratchpad to discover the API calls, then bake them into scripts.
- **Skip StableGen; build a custom ComfyUI img2img+ControlNet workflow driven over the HTTP `/prompt` API.** StableGen is a 3D *texturing* tool (it projects generated textures back onto meshes) — the wrong tool for per-panel 2D stylization. Your consistency comes from Blender render passes (depth + Freestyle line-art + normal + object-index) feeding ControlNet, plus a per-character LoRA and a fixed style LoRA. Base model: **SDXL** for the richest ControlNet/LoRA ecosystem and clean commercial license (OpenRAIL++-M).
- **The novel, defensible IP is the orchestration + the automated multi-axis evaluation/best-of-N selection loop, not any single component.** Everything else (3D-render→stylize, character-sheet LoRA, depth-ControlNet) already exists (Mickmumpitz, Dashtoon, Studio Orange do pieces of this). Your key insight — bootstrapping the character LoRA dataset FROM the 3D model (render many angles → stylize → train) — is a proven amateur/academic technique; execute it well rather than expecting it to be novel.

---

## Key Findings

1. **Blender MCP + Cursor** is real and mature for interactive use but wrong as a pipeline backbone. `ahujasid/blender-mcp` is 26.3k stars / 2.5k forks, MIT, last updated 2026-01-23, active; it supports Blender 3.6+ (not yet 5.0) and integrates PolyHaven/Sketchfab/Hyper3D-Rodin asset import. It cannot give you deterministic, version-controlled scenes. LLM spatial reasoning is the bottleneck: benchmarks (SCBench, OmniSpatial, BlenderBench) show frontier models top out ~50-58% on constructive/planning spatial tasks with a dominant "locally plausible, globally wrong" failure mode.
2. **Scripted bpy beats MCP for production.** SceneCraft (arXiv 2403.01248, ICML 2024) — the strongest academic LLM→Blender-code agent — plans a scene graph, emits bpy, and uses GPT-4V to iteratively refine, beating BlenderGPT by 45.1%/40.9% on CLIP score across synthetic and real-world datasets. The lesson is architectural: scene-graph → parametric code → render → VLM-critique → correct, all in version-controlled files.
3. **StableGen is a texturing tool, not a stylizer.** It uses SDXL/FLUX + ControlNet(depth/canny/normal) + IPAdapter to generate and *project textures onto 3D meshes* via a ComfyUI backend. GPL-v3, Blender 4.2+ (not 5.0), recently added a Qwen-Image-Edit workflow. For flat 2D panel stylization you want a plain ComfyUI img2img/ControlNet graph you control.
4. **Blender emits every conditioning signal you need natively:** Z/depth pass, Normal pass, a dedicated **Freestyle line-art render pass** (checkbox "As Render Pass" since 2.83), and **Object Index (cryptomatte/IndexOB)** masks for per-character regional conditioning. These map 1:1 onto ControlNet-depth, ControlNet-normal, ControlNet-lineart/canny, and regional prompt masks.
5. **Character consistency should be solved with a trained per-character LoRA bootstrapped from the 3D model**, not just IP-Adapter/InstantID/PuLID. Those adapters are trained on real faces and degrade on stylized art; InstantID drags reference lighting/pose, PuLID locks expression. They are complements (a cheap first pass or a fallback), not the primary solution.
6. **The render→stylize→train-LoRA bootstrapping loop is a documented, established workflow** (DCAI VRoid tutorial; Mickmumpitz character-sheet→FLUX-LoRA). The critical trick: run img2img on the CG renders (denoise ~0.4) and generate multiple style variants per pose so the LoRA learns *identity* not the *CG render look*. Failure modes: baked-in 3D look, lighting overfit, caption monotony.
7. **Automated evaluation must use style-robust metrics.** ArcFace/InsightFace identity similarity degrades badly on illustrated faces (it's trained on photographs). Use **DINOv2/DINOv3 and CLIP image embeddings** for stylized identity and location similarity; **SSIM/LPIPS + depth/edge re-extraction** for structure; and a **VLM-as-judge (Qwen3-VL 8B) in pairwise mode** for lighting/aesthetic. Pairwise beats pointwise substantially: GenArena (arXiv 2602.06013) shows Qwen3-VL 8B Instruct jumping 49.1%→60.5% on GenAI-Bench and 58.3%→83.7% on EditScore-Bench purely by switching from pointwise to pairwise — the pairwise 8B even beats the specialized EditScore-72B reward model (70.3%) and GPT-5 (75.5%).
8. **RL/preference-tuning of the diffusion model (Diffusion-DPO/DDPO/DRaFT/GRPO) is a "later, maybe" item**, not feasible as an early goal on 16GB. Collect the preference data now (free byproduct of best-of-N), defer the actual DPO fine-tune to rented cloud GPUs.

---

## Details

### 1. Blender MCP + Cursor maturity — and why to go code-first

**State of the tooling (as of Aug 2026).** `ahujasid/blender-mcp` is the reference implementation: 26.3k GitHub stars, 2.5k forks, MIT license, last updated 2026-01-23, active. Architecture is a Blender addon (`addon.py`) opening a socket server inside a live Blender session, plus an MCP server (`src/blender_mcp/server.py`) that any MCP client (Cursor, Claude Desktop, VS Code) talks to. It supports Blender 3.6+ (the maintainer notes 5.0 support is pending due to breaking API changes). Integrations: PolyHaven assets, Sketchfab, and Hyper3D/Rodin text/image-to-3D (you run your own Hunyuan3D server and it POSTs and imports the GLB). Run only one MCP client at a time.

**What it reliably does via natural language:** primitive creation, transforms, camera placement, basic lighting, material assignment, running arbitrary Python inside Blender, reading back the scene graph, and returning viewport screenshots as base64 (giving the agent visual feedback). For an interactive "make me a rough room" session it works well.

**Where it breaks down — and why this matters for a pipeline:**
- **LLM spatial reasoning is weak and non-deterministic.** This is the deep problem, not a tooling gap. Multiple 2025-2026 benchmarks converge: SCBench (arXiv 2604.09594) reports the highest-scoring frontier models (Claude Sonnet 4.5, Gemini 3 Pro Preview, GPT-5.2) attain only 57.6% accuracy on spatial reasoning, with the dominant failure being "Local-Only" — models produce locally plausible geometry but fail to enforce global constraints. OmniSpatial shows perspective-taking and geometric reasoning at ~30-40%; the BlenderBench/VIGA work shows one-shot camera-adjustment "fails" without iterative best-of-N search. For "put the camera at eye level 3m back, 15° off-axis, character A stage-left facing B" you will get plausible-but-wrong placements requiring correction loops.
- **Iterative correction loops burn tokens and drift.** Each correction re-sends scene state; scene state grows; runs diverge. There is no reproducibility guarantee: same prompt, different scene.
- **No version control.** A conversational scene isn't a diffable artifact.

**The recommendation: parametric bpy scripts run headless.** Have Cursor write Python that builds scenes from a declarative spec (JSON/YAML scene-graph → bpy). Run via `blender --background scene.blend --python build_and_render.py` (argument order matters; `-b` = background, `-o` output, `-f` frame). This is deterministic, version-controlled, diffable, parametrizable, and reproducible. Set fixed seeds and fixed render settings in the script. This mirrors what the strongest research systems actually do: **SceneCraft** (arXiv 2403.01248) models a scene graph as a blueprint, translates spatial relationships into numerical constraints in bpy, renders, and uses GPT-4V to critique and refine — beating BlenderGPT by 45.1%/40.9% CLIP score. Related lineage: **3D-GPT**, **BlenderGPT**, **BlenderLLM** (a domain-tuned model fine-tuned specifically to emit bpy), **LL3M** (multi-agent planner/retrieval/coder over a BlenderRAG knowledge base), **WorldCraft**, **BlenderAlchemy** (VLM-feedback material refinement).

**How to use MCP anyway:** as an interactive scratchpad. Let the agent explore in a live session to discover the exact bpy calls and asset names, then have Cursor crystallize those into the committed script. MCP for discovery, scripts for production.

**Alternatives to Blender for programmatic previs:**
- **Blender (recommended)** — best Python API for this job, native depth/normal/Freestyle/cryptomatte passes, free, huge ecosystem, Cycles renders headless without a display (EEVEE historically needed a GL context / Xvfb; use Cycles for headless robustness). `blenderless` (PyPI) and `blender-cli-rendering` are helpful references.
- **Three.js** — great if you want a browser-based blockout UI and the agent to emit JS; weaker for high-quality passes and offline batch.
- **Godot headless** — has an MCP server; lightweight; fine for blockout but you'd rebuild the render-pass pipeline.
- **Unity/Unreal headless** — Unreal's real-time previs is industry standard (used by pro layout artists) and has an unreal-mcp, but heavyweight to script and license-encumbered for redistribution.
- **USD/OpenUSD** — the right *interchange/versioning* format if this scales. Consider authoring scenes as USD and rendering via Blender's USD import, so scene state is a clean, diffable, tool-agnostic artifact. Good long-term bet; more upfront complexity.

### 2. Stylization: StableGen vs custom ComfyUI

**What StableGen actually is.** `sakalond/StableGen` (GPL-v3, Blender 4.2+, ComfyUI backend) is a **3D texturing** addon: it takes your 3D scene, uses multiple ControlNet units (depth/canny/normal) + optional IPAdapter style reference, generates images per viewpoint, and **projects/bakes them back onto the meshes as textures**, building a material node tree that blends views (Sequential mode = inpainting+visibility masks for consistency; Grid mode = faster multi-view). It recently added a Qwen-Image-Edit-2509 workflow. This is impressive but **it solves texturing 3D assets, not producing flat stylized 2D comic panels.** For your need it's the wrong abstraction — you don't want textured meshes, you want a 2D render restyled.

**The right tool: a custom ComfyUI img2img + ControlNet graph you own.** This is the industry-standard "3D → AI stylization" approach (Mickmumpitz's Blender→ComfyUI workflows, the RunComfy AI-rendering workflow). Configure Blender to output, per panel:
- **Beauty/flat render** (your img2img base latent).
- **Depth (Z) pass** — normalize via a Normalize node → ControlNet-depth.
- **Normal pass** → ControlNet-normal.
- **Freestyle line-art pass** — enable Freestyle in render settings, then View Layer → Freestyle → "As Render Pass"; feeds ControlNet-lineart or canny. Set object outline width deliberately.
- **Object Index / Cryptomatte** — assign each character/object a Pass Index → per-object masks for regional prompting and per-character LoRA masking.

These map cleanly onto SDXL ControlNets. Multi-ControlNet (depth + lineart, strengths ~0.5-0.8 each) is what pins composition, camera, and geometry — this is how you get camera/room/structure consistency "by construction."

**Base model choice in 2026 (with your RTX 5060 Ti 16GB + IP-ownership goal):**

| Model | VRAM (16GB?) | ControlNet/LoRA ecosystem | License (commercial) | Verdict |
|---|---|---|---|---|
| **SDXL** | Yes, comfortable + all add-ons | **Richest by far** (thousands of LoRAs/ControlNets; Pony/Illustrious/Animagine anime bases) | **CreativeML OpenRAIL++-M — commercial OK** | **Primary pick** |
| FLUX.1-dev | fp8/GGUF only on 16GB | Growing, still thinner | **Non-commercial** — blocks a sellable product | Avoid for shipping |
| FLUX.1-schnell | fp8/GGUF | Thin | **Apache 2.0 — fully commercial** | Backup if you need FLUX quality + license |
| FLUX.2-klein 4B | Fits | New, tiny | **Apache 2.0** | Watch |
| Qwen-Image (20B) | GGUF/Nunchaku 4-bit only | Growing; great in-image text | **Apache 2.0** | Good for lettering later |
| SD 3.5 Large | fp8 ~ tight | Very thin | Stability Community license | Skip |
| Z-Image Turbo 6B | Fits easily, ~8 steps | Tiny (new) | **Apache 2.0** | Watch for speed |

**Decision: SDXL as the workhorse** — it's the only choice that gives you mature multi-ControlNet, a deep LoRA ecosystem (essential for both your style LoRA and character LoRAs), comfortable 16GB headroom for ControlNet+LoRA+IP-Adapter simultaneously, and an unambiguous commercial license. Pick a strong stylized SDXL base (Illustrious/Pony/Animagine lineage for comic/manga) as your fixed checkpoint. Keep FLUX.1-schnell (Apache 2.0) or Qwen-Image as a secondary, license-clean high-fidelity path if SDXL quality plateaus.

**Style consistency techniques (use in combination):**
- **Style LoRA** trained on your target art style, applied at fixed weight on *every* panel — the single most reliable lever for panel-to-panel style consistency.
- **IP-Adapter style transfer** from a fixed style reference image (weight ~0.4-0.6, applied after any face adapter).
- **Fixed checkpoint + fixed sampler/CFG/seed strategy** across panels.
- **In-context/edit models (2025-2026):** FLUX.1 Kontext and Qwen-Image-Edit-2509 take a reference + structural conditioning and preserve identity/layout well (Kontext generally wins facial consistency and pose fidelity; Qwen is faster and does legible text). These are worth prototyping for a "restyle to match this reference panel" step, but note FLUX Kontext dev shares FLUX's non-commercial licensing concerns — verify before shipping. Content-preserving style transfer on DiTs is still hard (QwenStyle paper notes UNet-style disentanglement doesn't transfer cleanly to transformers).

**ComfyUI headless automation (essential — this is your pipeline spine).** Run ComfyUI as a server (`python main.py --port 8188`), export each workflow in **API format** (enable Dev Mode → "Save (API Format)"), then from Python: POST the workflow JSON to `/prompt` (returns a `prompt_id`), track progress via WebSocket `ws://host:port/ws`, and fetch outputs via `/history/{prompt_id}` then `/view`. Parametrize node inputs (prompt text, seed, LoRA name, input image paths) by editing the JSON dict before submission. Practical cautions from the field: one ComfyUI instance per GPU (single-threaded execution — don't fire concurrent `/prompt`s), use distinct `client_id`s, catch OOM as `execution_error` events (POST `/free` and retry), and parameterize checkpoint filenames per environment. The `ComfyUI-serverless`/ViewComfy patterns and the official `script_examples` are good references.

### 3. Per-character LoRA training for identity consistency

**The core strategy: bootstrap the LoRA dataset FROM your 3D model.** This is the key insight of your whole approach and it is a *proven, documented* workflow (not novel, but correct):

1. Render your low-detail 3D character from **many camera angles and poses** — front, 3/4, side, back; full body, upper body, face close-ups; several poses and expressions. Set model outlines to 0 and render clean at high res (e.g., 2048²) then downscale.
2. **Stylize the renders with img2img** into your target comic style (using a strong API model like your current Gemini/Nano-Banana, or a ComfyUI img2img pass at **denoise ~0.4**). Generate **2+ style variants per render** so the LoRA learns identity, not the flat-CG look. *This stylization step is non-negotiable* — training directly on raw CG renders bakes the 3D look in and it's very hard to remove.
3. **Train the character LoRA** on the stylized set.

Documented recipes: the DCAI VRoid tutorial uses ~50 stylized images across varied angles/framing and explicitly runs img2img at denoise 0.25-0.50 (recommends 0.40) to "prevent style fixation" (their words: "image to image can be used to create multiple image styles for the training source to prevent style fixation"). Mickmumpitz's character-sheet→FLUX-LoRA workflow trains on as few as 10-15 clean crops (~37 min on a 20GB card, per a vendor-adjacent writeup). Academic corroboration that "render synthetic multi-view → train adapter" is textbook: Hunyuan3D Studio (trains a LoRA on multi-view renders from arbitrary camera poses), StyleAvatar3D, SOAP, and DreamLight (which literally uses "bootstrapping" — train, add results to the training set, continue). For scale reference, academic multi-view protocols render 30-100 views per model; the hobbyist 10-50 is enough for a character LoRA.

**Failure modes to defend against (all confirmed):**
- **Baked-in 3D look** → the img2img stylization step + multiple style variants per pose. (DCAI: "If you let it train without changing the image style as it is, the style will remain strong… it would be difficult to get rid of the style completely.")
- **Lighting overfit** → render under varied light directions/HDRIs; don't train every image under one key light. (Academic relighting work — ReLi3D, DiLightNet — renders under many light directions specifically to prevent this; ReLi3D shows explicit "baked-in lighting" failure cases.)
- **Caption monotony / pose lock** → vary captions (describe subject, action, framing — not "an illustration of a person" repeated); vary poses AND expressions or the LoRA only does the trained pose. Train UNet-first; add text-encoder only at low LR. Hold out ~15 eval prompts and check every few hundred steps. Curation beats volume (community consensus: 60 good images > 200 indiscriminate).

**Training tooling (what fits 16GB in 2026):**
- **kohya_ss / sd-scripts** — the standard for SDXL LoRA. SDXL LoRA needs ~12GB min, 16GB comfortable. Supports SD1.5/SDXL/SD3/FLUX, LoRA/LoHa/LoKr/DreamBooth. Config-heavy but reproducible (save config files — good for your version-controlled pipeline).
- **OneTrainer** — friendlier GUI, good SDXL support.
- **ostris/ai-toolkit** — the go-to for FLUX/FLUX.2/Qwen/Z-Image LoRAs; has a low-VRAM mode that runs on 16GB (keep LowVRAM on). Author notes ranks below 32/32 gave poor results for some models.
- **FluxGym** (Kohya backend) — dead-simple FLUX LoRA UI supporting 12/16/20GB.

Since you'll standardize on SDXL, **kohya_ss/sd-scripts is your primary trainer.** Fused-backward-pass + Adafactor is the VRAM lever if you go near the edge or train FLUX later (Kohya v0.9.0, Jan 2025, brought FLUX LoRA down to 16GB and below).

**Concrete starting hyperparameters:**

*SDXL character LoRA (kohya):* rank/dim 32 (up to 64), alpha = rank or rank/2, LR ~1e-4 (UNet), text-encoder LR ~5e-5 or off initially, optimizer AdamW8bit (or Prodigy for auto-LR / Adafactor for low VRAM), resolution 1024 with bucketing, batch 1-2, ~1500-3000 steps for a character (watch the held-out samples for overfit rather than fixing a step count), a unique trigger token (e.g. `ch4r_alice`), regularization images optional for a single character but help prevent class bleed.

*FLUX character LoRA (ai-toolkit/FluxGym, if used later):* rank 16-32 (lower than SDXL), LR ~1e-4 but sweep 5e-5→2e-4 (FLUX is more LR-sensitive), Adafactor + fused backward for 16GB, LowVRAM on.

**LoRA vs adapters — when to use which:**
- **Trained LoRA** = your default. Best identity fidelity across novel poses/angles precisely because you trained it on your character from many angles.
- **IP-Adapter FaceID / InstantID / PuLID** = complements/fallbacks. Caveats for *stylized* work: all three use InsightFace/ArcFace embeddings tuned on real faces; InstantID is more color/lighting-stable and works better on stylized bases via landmark control but drags reference pose (needs a ControlNet to override); PuLID has highest fidelity but locks expression; FaceID is most flexible but lowest likeness ("cousin" effect). Use one of these for a *quick* first character before you've trained a LoRA, or as a light secondary conditioning. Do NOT rely on them as the primary identity mechanism for comic art. (Also note: InsightFace models carry non-commercial research terms — a licensing gotcha for a paid product, and another reason to prefer a trained LoRA.)

**Multi-character scenes without identity bleed** (the hard part when two character LoRAs are both applied globally — you get both faces blended):
- **Regional prompting / attention-couple / Latent Couple** driven by your **Blender Object-Index masks** — this is the elegant part: you already have exact per-character masks from the 3D scene, so you don't need to guess regions. Gate each character LoRA to its mask region.
- ComfyUI tooling: **Inspire Pack** (Regional Prompt / Regional IPAdapter / Regional Sampler + LoRA Block Weight), the newer Krea2-Regional (per-region LoRA gating, single-pass), or the **Impact Pack** for regional sampling.
- **Per-character inpainting passes** (two-pass: lock one identity at a time using its object-index mask) — slower but the most bleed-proof; good fallback when single-pass regional plateaus.
- Research context: CLoRA (contrastive test-time composition) shows naive LoRA-merge produces attribute bleed; masked/attention-gated composition is the fix.

### 4. Automated evaluation and candidate selection

This is where your defensible IP concentrates. Architecture: generate **best-of-N candidates** per panel (start N=4-8; ComfyUI batching), score each on your four consistency axes plus quality, then rank/threshold and auto-select.

**Metrics per axis (with the critical caveats):**
- **Character identity (STYLIZED):** ArcFace/InsightFace will **degrade badly on comic faces** — it's trained on photographs (the Arc2Face and stylization papers assume photoreal crops). Use **DINOv2/DINOv3 embedding cosine similarity** and **CLIP image-embedding similarity** against your reference character renders/turnaround. These are style-robust semantic embeddings (DINO-I is standard in consistency papers for pose/expression/semantic preservation). Build a small validation set: reference character sheet vs. generated panels; target e.g. **DINOv2 cosine ≥ 0.85** across 8 camera angles (tune the threshold empirically on hand-judged pairs first — treat 0.85 as a starting hypothesis, not gospel). Keep ArcFace as a *secondary* signal only if your art is semi-realistic.
- **Location/room:** DINOv2 or CLIP image similarity of the panel background vs. the reference render of that location.
- **Camera/composition/structure:** **re-extract depth and edges** from the stylized output (Depth-Anything-v2 / canny) and compare against the ControlNet conditioning input you fed in (SSIM on depth maps; edge IoU; or LPIPS). This directly measures "did the stylizer preserve my 3D-defined camera and geometry." This is the cleanest, most objective axis because you have ground-truth conditioning.
- **Lighting:** hardest to measure analytically. Options: histogram/luminance-direction comparison vs. the Blender render, or (more robust) a **VLM-as-judge** prompt asking about key-light direction and mood consistency vs. a reference. (Recent papers report a "Light-RMSE" metric for lighting consistency — worth borrowing.)

**VLM-as-judge for comic panels (2026):** Use **Qwen3-VL 8B Instruct** as the default open judge — the GenArena work (arXiv 2602.06013) designates it the default judge and shows **pairwise scoring massively beats pointwise** (49.1%→60.5% on GenAI-Bench, 58.3%→83.7% on EditScore-Bench just by switching to pairwise). Critically, pairwise Qwen3-VL 8B on EditScore-Bench (83.7%) *beats* the specialized EditScore-72B reward model (70.3%) and GPT-5 (75.5%). So: **always use pairwise/tournament comparison, not absolute 1-10 scores.** (Note: the public GenArena leaderboard itself is judged by the larger Qwen3-VL-32B Instruct FP8; if reliability matters more than speed, step up to 32B.) Known issues: position bias (randomize A/B slots and average), style bias, and self-consistency drift (run 3-5 times, take majority; report Krippendorff's α). InternVL3 and Qwen2.5-VL are viable alternatives; API models (GPT-5-class, Gemini) are more reliable but cost money and undercut your local-ownership goal — fine for calibration, not the hot loop. There's also `Qwen/Qwen-Image-Bench` (Q-Judger), a fine-tuned T2I quality judge outputting structured JSON scores, worth evaluating.

**Selection architecture:** weight the axes (structure and identity highest for your goals), gate on hard thresholds first (reject any candidate below structure/identity floors), then rank survivors by a weighted sum of the embedding scores + VLM pairwise win-rate. Emit the winner plus a scorecard per panel (this scorecard IS your preference dataset).

**RL/preference-tuning (Diffusion-DPO/DDPO/DRaFT/GRPO) — realistic assessment: "later, maybe."** The literature is rich and moving fast (DDPO/PPO framing of diffusion as an MDP; DRaFT/AlignProp differentiable-reward backprop; D3PO reward-model-free DPO; Diffusion-DPO CVPR 2024; DanceGRPO 2025 for visual generation; PPD/Personalized Preference Fine-tuning, Dang et al. CVPR 2025 / arXiv 2501.06655, which uses a VLM to extract preference embeddings and injects them via cross-attention, working from as few as 4 preference pairs on Stable Cascade). **But:** DPO on diffusion is very VRAM-hungry (it holds reference + policy denoising), and GRPO/PPO rollouts on DiTs are heavier still — these are 24GB+ (realistically multi-GPU/cloud) jobs. **Do this:** (a) collect preference pairs now for free from your best-of-N scorecards; (b) defer the actual Diffusion-DPO LoRA fine-tune to rented RunPod/Vast.ai A100/H100 time once you have a few thousand pairs; (c) LoRA-only DPO on the attention blocks is the consumer-feasible variant to try first. Don't let this block your v1.

### 5. PHASED BUILD PLAN (tasks for a Cursor coding agent)

**Recommended tech stack.** Python 3.11 (matches ComfyUI/uv defaults). Blender 4.2 LTS (StableGen/most tooling targets 4.2+, not 5.0 yet) invoked headless via `subprocess` (`blender -b scene.blend -P build_and_render.py`). ComfyUI as a persistent local server, driven via `/prompt` + `/ws`. kohya_ss for SDXL LoRAs. Config: **Pydantic** models + YAML per-panel specs. Caching: content-hash renders and conditioning maps (skip re-render if scene spec + seed unchanged). Determinism: pin every seed; pin sampler/steps/CFG; pin model + LoRA hashes. Asset/version management: **git** for code + scene specs (JSON/USD), **git-lfs or DVC** for 3D assets, renders, and `.safetensors` LoRAs; a manifest mapping character→LoRA hash→training-set hash. Metrics libs: `torch`, `open_clip`/`transformers` (DINOv2, CLIP), `insightface` (secondary), `scikit-image`/`lpips`, Depth-Anything-v2. Orchestration: a thin Python package; consider Prefect/simple DAG later.

**Recommended repo structure:**
```
comic-pipeline/
  pyproject.toml
  config/            # pydantic settings, model paths, thresholds
  specs/             # per-panel & per-storyboard YAML/JSON scene specs (versioned)
  blender/
    build_scene.py   # spec -> bpy scene graph
    render_passes.py # configures depth/normal/freestyle/object-index AOVs
    run_headless.py  # subprocess wrapper
    assets/          # low-poly characters, rooms (git-lfs/DVC)
  comfy/
    client.py        # /prompt + /ws HTTP client
    workflows/       # API-format workflow JSON templates (versioned)
    stylize.py       # inject conditioning + LoRAs, submit, retrieve
  lora/
    bootstrap.py     # render turntable -> stylize -> build dataset
    train_sdxl.py    # kohya invocation + config
    registry.json    # character -> lora hash -> dataset hash
  eval/
    identity.py      # DINOv2/CLIP similarity
    structure.py     # depth/edge re-extract + SSIM/LPIPS
    lighting.py      # histogram / VLM
    vlm_judge.py     # Qwen3-VL pairwise
    select.py        # best-of-N ranking + thresholds
  pipeline/
    panel.py         # single-panel orchestration
    storyboard.py    # multi-panel sequencing
  cache/             # content-hashed renders & conditioning
  outputs/
  tests/
```

---

**PHASE 0 — Simplest end-to-end vertical slice (prove the chain).**
- *Goal/done:* One hardcoded 3D scene (a room + one character primitive), one camera, one Cycles render, one ComfyUI img2img stylization pass, one output PNG panel. No consistency machinery.
- *Files:* `blender/run_headless.py`, `blender/build_scene.py` (hardcoded), `comfy/client.py`, `comfy/stylize.py`, `pipeline/panel.py`.
- *Acceptance:* Running `python -m pipeline.panel` produces `outputs/panel_000.png` from scratch with zero manual steps; re-running with the same seed produces a **byte-identical or near-identical** render (proves determinism). ComfyUI called purely over HTTP.
- *Effort:* Low-Medium (2-4 days). *Risk:* Low. *Deps:* none.

**PHASE 1 — Render passes / AOVs + ControlNet conditioning.**
- *Goal/done:* Blender emits depth, normal, Freestyle line-art, and object-index passes; ComfyUI workflow consumes depth+lineart via multi-ControlNet so the stylized panel provably follows the 3D geometry.
- *Files:* `blender/render_passes.py`, `comfy/workflows/stylize_controlnet.json`, update `stylize.py`.
- *Acceptance:* `eval/structure.py` re-extracts depth/edges from the output and scores **SSIM(depth) ≥ 0.7** and edge-IoU above a hand-tuned floor vs. the conditioning input, across 3 test cameras. Visual check: camera/room match the 3D.
- *Effort:* Medium (3-5 days). *Risk:* Medium (Freestyle-as-pass + normalize wiring is fiddly). *Deps:* Phase 0.

**PHASE 2 — Fixed style LoRA + style consistency.**
- *Goal/done:* Train (or acquire) one style LoRA; apply at fixed weight on every panel; lock checkpoint/sampler. Panels look like one consistent comic style, not "AI slop."
- *Files:* `lora/train_sdxl.py` (style variant), style LoRA in `registry.json`, update `stylize.py`.
- *Acceptance:* Across 10 panels of *different* scenes, pairwise Qwen3-VL judge rates style consistency; CLIP style-embedding variance below a set threshold. Human gut-check: reads as intentional art.
- *Effort:* Medium. *Risk:* Medium (style-LoRA quality). *Deps:* Phase 1.

**PHASE 3 — Character LoRA bootstrapped from 3D (the centerpiece).**
- *Goal/done:* `lora/bootstrap.py` renders a character turntable (many angles/poses/expressions), stylizes each (img2img denoise ~0.4, 2 variants each), builds a captioned dataset, and `train_sdxl.py` trains the per-character LoRA. Character stays consistent across novel poses.
- *Files:* `lora/bootstrap.py`, `lora/train_sdxl.py`, `lora/registry.json`.
- *Acceptance:* Generate the character in **8 held-out camera angles** not in the training set; **DINOv2 cosine ≥ 0.85** (starting target; calibrate) vs. reference sheet; no baked-CG look (VLM check); expression/pose variety preserved.
- *Effort:* High (1-2 weeks incl. iteration). *Risk:* High (overfit, baked look, lighting). *Deps:* Phases 1-2.

**PHASE 4 — Location reuse + full single-panel consistency.**
- *Goal/done:* Reusable versioned 3D locations; a panel spec references a location + character(s) + camera; all four axes (camera, lighting, room, character) hold "by construction."
- *Files:* `specs/` schema, `blender/build_scene.py` (spec-driven), `eval/identity.py`, `eval/lighting.py`.
- *Acceptance:* Same location across 5 panels scores DINOv2(background) ≥ 0.9; character identity ≥ 0.85; lighting consistency passes VLM pairwise. Full `eval/` scorecard emitted per panel.
- *Effort:* Medium-High. *Risk:* Medium. *Deps:* Phase 3.

**PHASE 5 — Multi-character scenes (regional, mask-driven).**
- *Goal/done:* Two+ character LoRAs in one panel, gated by Blender object-index masks via regional prompting; no identity bleed.
- *Files:* `comfy/workflows/stylize_regional.json`, `comfy/stylize.py` (mask injection), Inspire/Krea2-Regional nodes.
- *Acceptance:* In a 2-character panel, each face scores identity ≥ 0.85 against its *own* reference and < a bleed threshold against the *other's* reference.
- *Effort:* High. *Risk:* High (bleed is the classic failure). *Deps:* Phase 4.

**PHASE 6 — Multi-panel storyboard sequencing.**
- *Goal/done:* `pipeline/storyboard.py` takes a storyboard spec (ordered panels, shared characters/locations, camera list) and produces a full page/sequence with cross-panel consistency and caching.
- *Files:* `pipeline/storyboard.py`, cache layer.
- *Acceptance:* A 6-panel sequence generates unattended; cross-panel identity/location/style all above thresholds; cache hit skips unchanged renders.
- *Effort:* Medium. *Risk:* Medium. *Deps:* Phase 5.

**PHASE 7 — Automated evaluation + best-of-N selection.**
- *Goal/done:* Generate N candidates per panel, score all axes, threshold+rank, auto-select winner, log scorecards. Human review only on low-confidence panels.
- *Files:* `eval/select.py`, `eval/vlm_judge.py`, batch generation in `stylize.py`.
- *Acceptance:* On a labeled set of ~30 panels, auto-selected winner agrees with human pick **≥ 70%** of the time (pairwise-VLM realistic ceiling); low-confidence flagging catches the disagreements.
- *Effort:* High. *Risk:* Medium-High (judge reliability). *Deps:* Phase 6.

**PHASE 8 — (Later, maybe) RL/preference fine-tune.**
- *Goal/done:* Use accumulated best-of-N preference pairs to Diffusion-DPO LoRA-tune the stylizer on rented cloud GPU.
- *Acceptance:* DPO-tuned model raises auto-selection win-rate / reduces N needed, measured on held-out panels.
- *Effort:* Very High. *Risk:* Very High / research-grade. *Deps:* Phase 7 + cloud budget. **Explicitly optional.**

### 6. Prior art — where you're reinventing vs. where the novelty is

**Existing tools doing pieces of this:**
- **Dashtoon Studio** — AI comic/manga platform, consistent-character library, text-to-image; **pure prompt/diffusion, no 3D previs** (trains its own diffusion models; per a Microsoft case study generates 50k+ images/day).
- **Lore Machine** — long-form text → LLM parses characters/scenes → SD renders ordered storyboard; **pure prompt/diffusion.**
- **AI Comic Factory** (open-source, jbilcke-hf) — LLM + SDXL panels from a prompt; no 3D, no character LoRA (identity consistency is a known weakness).
- **Storyboarder.ai** — AI storyboards + a 3D-camera tool that re-angles a *generated* frame (not your own 3D model). **Boords** — collaborative AI storyboards, explicitly no 3D.
- **Clip Studio Paint 3D models** — poseable 3D figures as *manual* drawing reference (the human draws over them). The manual analog of your idea.
- **Cascadeur** — 3D keyframe animation with AI auto-posing; a tool to pose your character, not a stylizer.
- **Mickmumpitz** — the closest public work: character-sheet→FLUX-LoRA, and Blender→ComfyUI depth/lineart stylization; his short "Paper Jam" used "hand-animated poses in an AI-generated 3D space… rendered with Flux + regional custom character LoRAs" — essentially your hybrid, done manually per project.
- **Professional anime (Studio Orange — Beastars, Trigun Stampede)** — genuinely animates in 3D then has 2D artists redraw/correct over it for consistency (Sakuga Blog on Land of the Lustrous: "right about any close-up… is actually a 2D drawing"). Validates your *concept* at the top level, but it's hand-craft, not AI. Also PrevizWhiz (arXiv 2602.03838) — a research system doing exactly "rough 3D scenes + generative models → stylized previz," and FrameForge/ShotPro on the 3D-previs side (FrameForge won a Technical Achievement Emmy).

**Where you'd be reinventing:** LLM-script-to-panels, prompt-based comic generation with a character library, character-sheet→LoRA, and 3D-render→depth/lineart→stylize are all done. Don't rebuild those from zero — study Mickmumpitz's workflows and the RunComfy AI-rendering workflow first.

**Where the genuine, defensible novelty is:** (1) the **integrated, automated orchestration** — user's own low-detail 3D model → auto-rendered multi-angle stylized dataset → auto-trained per-character LoRA → mask-driven multi-character panels → storyboard sequencing — as one unattended system (no shipping product bundles this end-to-end from a user-supplied 3D model); and (2) the **multi-axis automated evaluation + best-of-N selection loop** with style-robust metrics and a VLM judge, and the preference dataset it produces. Concentrate your IP effort there.

### 7. IP and licensing

- **SDXL:** CreativeML OpenRAIL++-M — permits commercial use of model and outputs. **Safe for a sellable product.** Your single best base-model choice for IP cleanliness + ecosystem.
- **FLUX.1-dev:** **Non-commercial license** — you generally may use images but cannot build a commercial product/service on the dev weights without a BFL commercial license. **Avoid for shipping.** FLUX.1-schnell and FLUX.2-klein 4B are **Apache 2.0 — fully commercial.** FLUX.2-klein 9B reverts to non-commercial.
- **Qwen-Image, Z-Image:** **Apache 2.0** — commercial-safe (great for lettering/text panels and as a license-clean high-fidelity path).
- **SD 3.5:** Stability Community license — restrictions above revenue thresholds; read carefully.
- **ControlNet weights:** check each; the canonical SDXL ControlNets are generally permissive, but verify per-file. **InsightFace models used by FaceID/InstantID/PuLID carry non-commercial research terms** — a real gotcha if you rely on them in a paid product, and another reason to prefer a trained LoRA.
- **LoRAs you train on your own artwork:** yours. Training a *style* LoRA on your own drawn art is the cleanest IP position and strengthens your "own it / sell it" goal. Avoid training on others' copyrighted art if you intend to sell.
- **Blender (GPL):** Blender itself is GPL, **but the GPL covers Blender's code, not your outputs or your scripts.** Renders you make are yours. Python scripts you write that call bpy and run *inside/alongside* Blender are generally considered yours to license as you wish (the FSF/Blender position is that scripts run by Blender are not automatically derivative works) — **but if you distribute a Blender *addon* or bundle/modify Blender itself, GPL obligations attach.** Practically: use Blender as a tool invoked via `subprocess`, ship your pipeline as a separate program that *calls* Blender rather than embedding or redistributing it, and you keep your code under whatever license you choose. If you ever ship a `.py` addon installed into Blender, treat that addon as GPL.
- **StableGen:** GPL-v3 — if you were to distribute a fork/derivative it'd be GPL; you're not using it, so moot.

**Bottom line on IP:** build on SDXL (+ Apache-2.0 Qwen/schnell as needed), train your own style and character LoRAs on your own/licensed art, invoke Blender as an external tool, and keep your orchestration + evaluation code proprietary. That stack is cleanly sellable, and your defensible moat is the orchestration + eval loop, not the models.

---

## Recommendations (staged, with decision thresholds)

1. **Now — commit to code-first + SDXL.** Stand up Phase 0 this week. Use Blender MCP interactively only to learn the bpy calls, then have Cursor write `build_scene.py`. Decision gate: if the determinism check fails (renders vary run-to-run), fix seeds/settings before proceeding — non-determinism poisons everything downstream.
2. **Phases 1-2 — lock structure and style.** These give you camera/room-by-construction and one coherent art style. Gate to Phase 3 only when SSIM(depth) ≥ ~0.7 and style reads as intentional (not slop) on a 10-panel spread.
3. **Phase 3 — invest here; it's the make-or-break.** Nail the bootstrap loop: img2img-stylize renders at denoise ~0.4, 2+ variants/pose, varied poses/expressions/lighting, UNet-first training, held-out eval. Gate: DINOv2 identity ≥ 0.85 on 8 held-out angles with no baked-CG look. If you can't hit this after dataset/caption iteration, fall back to InstantID+ControlNet as an interim identity crutch (accepting stylization limits and the InsightFace non-commercial caveat) while you improve the dataset.
4. **Phases 4-6 — scale to storyboards.** Add locations, multi-character regional masking, sequencing. Gate multi-character (Phase 5) on the bleed metric (own-identity ≥ 0.85, cross-identity below threshold); if single-pass regional bleeds, switch to two-pass masked inpainting.
5. **Phase 7 — build the eval loop early-ish and treat it as your product.** Use Qwen3-VL 8B **pairwise** (step to 32B if reliability matters more than speed). Gate: auto-selection agrees with human ≥ 70% on a 30-panel labeled set. Below that, the judge isn't ready to run unattended — keep humans in the loop and improve prompts/thresholds.
6. **Phase 8 — defer RL.** Only start Diffusion-DPO once you have a few thousand preference pairs AND cloud GPU budget. Benchmark that changes the call: if best-of-N with N≥8 already clears your quality bar reliably, you may never need DPO.

**Hardware reality check (RTX 5060 Ti 16GB):** SDXL inference + multi-ControlNet + LoRA + IP-Adapter fits comfortably. SDXL LoRA training fits (16GB is "comfortable" per 2026 guides). FLUX LoRA training fits *only* with LowVRAM/fused-backward and is slow — prefer SDXL locally. Diffusion-DPO/GRPO fine-tuning does **not** fit — rent RunPod/Vast.ai (A100/H100) for that. Qwen-Image/FLUX-dev full-precision inference needs quantization (GGUF/fp8) on 16GB.

## Caveats
- **Fast-moving area.** Model/license facts (FLUX.2 variants, Z-Image, Qwen-Image) are Q1-2026 snapshots from secondary tech blogs; **verify each model card's license yourself before shipping** — licenses change and blog summaries occasionally lag.
- **The 0.85 DINOv2 / 0.7 SSIM / 70% agreement targets are starting hypotheses**, not validated constants for your art style. Calibrate them against a small hand-judged set early; stylized-domain thresholds vary.
- **ArcFace on comic faces is a known trap** — several papers show identity metrics assume photoreal crops. Trust DINOv2/CLIP for stylized identity and treat any ArcFace number skeptically.
- **VLM judges have position/style bias and self-inconsistency** — randomize A/B, run multiple times, report agreement (Krippendorff's α); don't over-trust a single verdict.
- **Some arXiv IDs surfaced by search carried implausible future dates** (e.g. 26xx.xxxxx); the *methods* (SceneCraft, PrevizWhiz, GenArena pairwise finding, the bootstrapping approach) are corroborated across multiple sources, but treat exact citation IDs of the newest papers with mild caution.
- **Several performance figures are vendor/community-sourced** (Mickmumpitz "37 min on 20GB," "10-15 crops," Dashtoon "50k images/day") — directionally reliable, not benchmarked guarantees.
- **Blender 5.0 support is still maturing** across the addon ecosystem (StableGen, MCP) — standardize on Blender 4.2 LTS for now.
- **The private repo could not be read**, so this plan may duplicate or diverge from work you've already done; reconcile against your existing `ComicMainEngine` code.