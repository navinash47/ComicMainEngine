# ComicMainEngine

Code-first pipeline for the onceuponatime AI history comic. Phase 0–2 focused: tracked API usage + local live analytics.

## Setup (Mac)

```bash
cd ~/Desktop/ComicMainEngine
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
cp ~/Desktop/env.txt .env
# Fix any spaces around '=' in .env (e.g. ANTHROPIC_API_KEY=sk-...)
```

## Commands

```bash
# Live analytics + TaskObserver → http://127.0.0.1:8765
python scripts/run_dashboard.py

# Global tasks CLI (same SQLite board the webpage uses)
python scripts/tasks.py list
python scripts/tasks.py start phase3 --note "beginning bake-off"
python scripts/tasks.py done phase3

# ~pennies: hello to Anthropic / OpenAI / Gemini (tokens logged)
python scripts/ping_apis.py

# Phase 1: one Nano Banana image (~$0.04 with flash-image)
python scripts/phase1_generate.py

# Phase 2: 3 style samples (default; use --count 9 for full grid)
python scripts/phase2_style_grid.py
```

TaskObserver lives in `data/usage.db` (`task` table). Every `/api/summary` poll re-derives status from API calls + `outputs/`, so the board updates itself globally across scripts and the webpage.

## Layout

```
src/comicengine/   # config, pricing, tracked clients, style, usage DB
dashboard/         # FastAPI + static live page
scripts/           # phase0–2 CLIs
notebooks/         # reserved for later .ipynb phases
outputs/           # generated images (gitignored)
data/              # SQLite ledger (gitignored)
```

## Notes

- Production finals later: Gemini 3 Pro Image (Nano Banana Pro). Phase 1–2 default to **Flash Image** to save money.
- Local FLUX (Windows RTX 5060 Ti + CUDA 12.8) is for free R&D only — non-commercial model license for FLUX.1 dev.
- Do **not** commit `.env`. Rotate keys if they were pasted into chat.
