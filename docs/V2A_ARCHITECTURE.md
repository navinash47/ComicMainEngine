# Version 2A — Storyboard-first comics

Readable without running code. Program state lives in [`data/v2a_program.json`](../data/v2a_program.json). One commit per phase gate. Branches: `phase-v2a-a0` … `phase-v2a-a5`.

**Dashboard:** local admin → **Version 2A** → [`/v2a`](http://127.0.0.1:8770/v2a) (ComicEngine is on **8770**; 8765 is Procedural City). Architecture markdown: [`/v2a/architecture`](http://127.0.0.1:8770/v2a/architecture). API: `/api/v2a/program`. This is a live view of the JSON — it does not replace Version 2 (phases 12–20).

## Version 2 stays frozen

**Version 2** (`data/v2_program.json`, phases 12–20: feedback harvest → sync → incident ledger → mistake-memory → product waves → knowledge graph → critic/DPO) is a **separate, frozen track**. Do not edit `data/v2_program.json` from 2A work. Do not rewrite Version 2 phases to become storyboard-first. 2A is a **parallel program** with its own JSON, docs, and branches.

Version 2 remains the text/feedback learning loop on the existing reader. Version 2A is the storyboard-first image path.

---

**Idea:** you own composition. You draw a stick figure or light sketch. The model enhances under locked character, location, and lighting bibles. The page should not look like default AI manhwa.

**Honest limit:** “does not look AI at all” is not one API call. It is your lines + an ink/print style lock + high structural control + a human cleanup pass on hero pages. Do not fine-tune a foundation model on every panel. Collect approved pairs, then distill.

**This is a genre-agnostic framework.** The first fixture is a Ramayana slice so we can test desire, insult, war, intrigue, magic, abduction, and grief in the same slots. Any later genre (Mahabharata, history, romance, original) should drop into those same slots.

---

## Routing (do not invert)

| Traffic | Where | Keys |
|---|---|---|
| Text / scripts / Story Architect | **OmniRoute** `localhost:20128` (`USE_OMNIROUTE=1`) | `OMNIROUTE_API_KEY` |
| Images (Nano Banana / Gemini, Flux, Kontext, LoRA later) | **Direct provider APIs** | `GOOGLE_API_KEY`, fal keys from project `.env` |

Never route Nano Banana / Flux / GPT-Image / other image models through OmniRoute. Gemini text hellos stay direct Google. Same rule as the rest of ComicEngine.

---

## How 2A differs from today

Today (Version 1 / current pipeline) is **text → image**:

```
StorySpec → script_engine (OmniRoute) → Episode JSON
  → character ref sheets → gemini_ref / flux_kontext → speech bubbles
```

That path already has:

- `script_engine.py` — OmniRoute structured scripts; default voice `dad_to_daughter_bedtime`
- `episode_schema.Character` — `id`, `display_name`, `role`, `look`, `notes` only
- `panel_batch.py` — `gemini_ref` (`gemini_image_with_refs`) then `flux_kontext` (`fal_kontext_edit`) then `text_only_fal`
- `styles.py` — default lock `korean_manhwa` (clean cel, expressive eyes, polished digital)

It still **invents camera and pose from words**, which is why faces and lighting drift — and why `korean_manhwa` reads as default AI manhwa.

Version 2A inverts the image step: **you draw the shot; AI fills under locks**.

```
vague story + draft bibles
  → Story Architect (epic map, enhanced cast, script)
  → Scene Director (shot cards: camera, light, blocking)
  → you draw storyboards
  → ingest (tag sketch to episode + panel)
  → enhance (sketch + char lock + location lock + light recipe)
  → human approve / light ink / reject
  → panel memory (last-N approved frames)
  → periodic distill (LoRA / critic), not live weight updates
```

---

## Layer 1 — Story Architect

You bring a vague-but-detailed story plus rough character notes. The system (OmniRoute **text only**) does not jump to panels. It builds an architecture, then a script.

Outputs, in order, each with a human gate:

1. **Epic map** — book / kanda / parva → arc → episodes (8–14 pages each).
2. **Enhanced character bibles** — see schema notes below.
3. **Fact / tradition sheet** — reuse `FactCheckItem` (`supported` / `disputed` / `simplified` / `dramatized`). Never invent theology as fact.
4. **Scene list** — dramatic purpose, who is on stage, what changes.
5. **Script with dialogue** — still an `Episode`, but panels start as **shot cards**, not `art_prompt` guesses.

Reuse `StorySpec` in `script_engine.py`. Do **not** default 2A voice to `dad_to_daughter_bedtime` or manhwa looks.

---

## Layer 2 — Scene Director + your storyboards

For each scene the system writes a **shot card** you then draw:

- Camera: distance, angle, what is cropped
- Lighting: time of day, key direction, shadow hardness, palette
- Blocking: who stands where, eyelines
- Continuity: costume, wounds, props, weather from the previous approved panel

You enhance that card with a stick figure or light sketch. Paper photo, tablet PNG, or later an in-dashboard canvas are all valid. Ingest deskews and extracts lines. The sketch is the **composition contract**. The model is not allowed to restage the scene.

---

## Layer 3 — Enhance, memory, then distill

Each panel is conditioned on four things at once:

| Input | Role |
|---|---|
| Your sketch | Pose, camera, composition (high control) |
| Character lock sheets | Face, body, costume (turnaround + expressions) |
| Location lock | Same architecture and materials |
| Lighting recipe | Same key light and palette for the whole scene |

**Do not start by fine-tuning a foundation model on each panel.**

1. **Now (no training):** sketch-conditioned img2img / ControlNet-scribble or Flux Kontext with the sketch as the structure image, plus Gemini multi-ref for faces (`gemini_image_with_refs`, `fal_kontext_edit`). New 2A style preset — **not** `korean_manhwa`. Ink + paper + flat or gouache. Negatives: plastic skin, glow, extra fingers, AI sheen. Image APIs stay **direct** (never OmniRoute).
2. **After ~30–80 approved pairs:** dataset `(sketch, refs, shot card) → approved panel`. Train a style LoRA and one LoRA per lead. Local Flux LoRA on the RTX 5060 Ti is enough when we get there.
3. **Distill, don’t retrain the world:** a small student (prompt rewriter + “matches sketch / face / light?” critic). Visual twin of Version 2 phases 18–19, which stay text/feedback-only.

Knowledge between panels is a **bible + last-N approved frames**, not live weight updates. Weights update on a schedule (end of episode / end of arc).

Human gate on every panel: approve, light ink, or reject with a Version 2 taxonomy code (`identity_drift`, `continuity`, `prompt_art_miss`, …).

---

## Schema notes (do not change live `episode_schema.py` in A0)

A later implementation phase will add these. Until then they are contracts.

### `CharacterBible` (extends today’s `Character`)

Today: `id`, `display_name`, `role`, `look`, `notes`.

Add:

- `voice` — how they speak
- `relationships` — list of `{other_id, relation, note}`
- `costume_variants` — `{id, when, look}` (exile vs court vs wounded)
- `iconography` — must-keep marks (respectful, not kitsch)
- `never_do` — e.g. “never lose Ravana identity to the reader in disguise”
- `sheet_paths` — turnaround / expression / variant PNG paths

### `LocationLock`

- `id`, `display_name`, `look`, `materials`, `recurring_props`
- `sheet_path`

### `LightingRecipe`

- `scene_id`, `time_of_day`, `key_direction`, `shadow`, `palette` (3–5 hex or names)

### `ShotCard`

- `episode_id`, `panel_index`, `camera`, `lighting` (ref or inline), `blocking`, `continuity_from`
- `dramatic_purpose`

### `Storyboard`

- `episode_id`, `panel_index`, `source_path` (photo or PNG), `normalized_path`
- `status`: `ingested` | `approved_lines`

Today’s `Panel.art_prompt` is a fallback only. In 2A the sketch + shot card are primary.

### Epic graph

```
Epic → Book/Kanda/Parva → Arc → Episode → Scene → Panel
```

Hundreds of characters can exist as sheets. Only ~8–12 leads get LoRAs. Crowds use a crowd rule, not individual bibles.

---

## Not-AI rules

- Do not use `korean_manhwa` as the 2A style lock.
- Prefer line-art two-stage: ink follows the sketch, then color only.
- Human ink on hero pages (covers, capture, Jatayu’s death).
- High ControlNet / Kontext weight on the sketch; restaging is a fail.
- Reject plastic skin, over-smooth gradients, glow, extra limbs.
- Pillow blank-frame QA is not enough (Version 1 already learned this).

---

## Alternative methods (stay inside 2A)

If sketch→enhance is not enough:

1. **You ink, AI only flats/colors** — strongest non-AI look; slowest. Hero pages.
2. **2D puppets** — pose a locked turnaround; AI does background and light.
3. **3D blockout** — Blender mannequins for war/crowds; easy to look CG if overused.
4. **IP-Adapter / Redux without LoRA** — cheaper consistency before training data.
5. **Line-art two-stage** — default for 2A.
6. **Traditional + AI in-betweens** — after a style LoRA exists.

Default: **(5) + (1) on hero pages**. Use (2)/(3) only when crowds break.

---

## Test series: Aranya — The Capture (episodes 1–10)

**Not** “the product is only Ramayana.” This is the first fixture to prove mixed genre fits the same slots.

**Tone (locked):** adult stark — desire and violence are explicit and readable; no exploitation, no gore-porn, no kitsch gods. Not bedtime. Not all-ages ACK softening.

**Map:** Ramayana → Aranya Kanda → “The Capture” (Surpanakha’s desire → Sita taken → Jatayu’s testimony).

**Leads (A1 bibles):** Rama, Sita, Lakshmana, Surpanakha, Ravana, Maricha, Jatayu.

**Supporting:** Khara, Dushana (ep 3). Pushpaka is a location-object.

**Locations:** Panchavati ashram, Dandaka forest, Khara’s field, Lanka court, sky/Pushpaka path, Jatayu’s fall site.

Each episode is 8–14 pages. Each has a story goal, a framework goal, and a gate.

### Ep 1 — Surpanakha sees Rama

- Story: Panchavati; she is struck by Rama; proposes; he refuses and points her to Lakshmana.
- Framework: desire + two-person blocking + forest light lock. Cast: Rama, Surpanakha, Sita glimpsed.
- Gate: bible looks hold; shot cards make her approach readable without restaging.

### Ep 2 — The insult

- Story: Lakshmana rejects her; the mutilation (nose/ears) is consequence, not spectacle; she flees cursing.
- Framework: adult violence without gore-porn; her face **before vs after**.
- Gate: two Surpanakha sheets (whole / wounded); you signed the violence line.

### Ep 3 — Khara’s war

- Story: she brings Khara–Dushana; Rama fights; the rakshasa force falls.
- Framework: crowd/war (3D blockout is a later backup); Rama identity in action.
- Gate: battlefield location lock + crowd rule; Rama still matches ep 1.

### Ep 4 — Report to Lanka

- Story: Surpanakha before Ravana; she describes Sita; his pride turns to wanting her.
- Framework: new location (Lanka court) + new lead (Ravana) + wounded-Surpanakha continuity.
- Gate: Ravana bible + Lanka lock signed; her wound still present.

### Ep 5 — Maricha’s counsel

- Story: Ravana recruits Maricha; golden-deer plan; Maricha’s fear.
- Framework: two-hander intrigue; Ravana consistency from ep 4.
- Gate: Maricha bible; plan fact-checked as dramatized Valmiki beat.

### Ep 6 — The golden deer

- Story: Sita wants the deer; Rama hunts; Maricha’s dying cry in Rama’s voice.
- Framework: magic/creature + off-screen voice; Sita + ashram lock from ep 1.
- Gate: deer design locked; ashram matches ep 1; cry labeled dramatized.

### Ep 7 — The empty hut

- Story: Sita sends Lakshmana; threshold / rekha (mark dramatized vs tradition); Ravana as ascetic.
- Framework: three-person exit + disguise (Ravana readable to us, not to Sita).
- Gate: disguise sheet + “never lose Ravana identity to the reader.”

### Ep 8 — The capture

- Story: Ravana seizes Sita; Pushpaka; she resists.
- Framework: abduction staging (adult, not exploitation); sky/chariot; Sita continuity.
- Gate: you signed the capture boards; Sita face matches ep 1/6.

### Ep 9 — Jatayu’s stand

- Story: Jatayu fights Ravana; wings cut; Sita drops jewels.
- Framework: aerial fight + new lead + jewel prop trail.
- Gate: Jatayu bible; jewels are a continuity prop, not a one-off.

### Ep 10 — Jatayu tells Rama

- Story: empty ashram; dying Jatayu; Rama learns who took Sita; vow.
- Framework: grief + testimony + callback to ep 1 location and ep 9 wounds.
- Gate: ashram + Jatayu wounded sheet match; series recap one-pager exists.

A1 writes all 10 packets (no images). A3 bake-off renders **3 panels from one scene**, not all 10. Recommended prove scenes: ep 1 approach, ep 8 capture, or ep 10 Jatayu.

---

## Phase gates (one commit each)

When a gate passes: commit on that phase branch, update the living report only if images/evals ran, merge to `master`. Do not batch two phases into one commit.

| Phase | Goal | Done when | Commit |
|---|---|---|---|
| **A0** Architecture freeze | 2A is readable without running code | This doc + `data/v2a_program.json` with exit gates; live `episode_schema.py` unchanged | `phase-v2a-a0: freeze storyboard-first architecture beside Version 2` |
| **A1** Story Architect | Signed adult-stark Capture series | Epic map; bibles for all leads (Surpanakha whole+wounded; Ravana king+ascetic); fact verdicts; 10 episode packets; you signed | `phase-v2a-a1: architect the 10-episode Aranya capture test series` |
| **A2** Shot cards + ingest | A real sketch stores against a panel id | Shot cards per scene; ingest photo/PNG → `storyboard_path`; one real sketch end-to-end | `phase-v2a-a2: shot cards plus storyboard ingest for tagged panels` |
| **A3** Sketch-conditioned enhance | Fill your lines; ink/print, not manhwa | ≥2 methods × ≥3 panels from **one** Capture scene; style lock signed; no restage; ledger + report | `phase-v2a-a3: lock sketch-conditioned enhance and ink style` |
| **A4** Panel memory | Panel N+1 uses approved N | Approve/ink/reject + taxonomy; last-N refs passed in; 3-panel face/light hold | `phase-v2a-a4: panel memory constrains the next enhance` |
| **A5** Distill | Model improves on *your* sketches, on a schedule | ≥30 approved pairs; style/lead LoRA **or** critic beats baseline; no live PPO | `phase-v2a-a5: distill from approved storyboard pairs` |

A0 is this commit. A1–A5 stay `locked` in `v2a_program.json` until you start that phase.
