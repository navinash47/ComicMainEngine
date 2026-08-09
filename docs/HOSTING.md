# Dual hosting — ComicEngine (both on Vercel)

Two **separate** Vercel projects. Share them differently:

| Site | Who | Folder | What they see |
|------|-----|--------|----------------|
| **Reader** | customers / testers | `feedback-beta/` | Register/login, comics, panel + story ratings |
| **Admin** | you + fellowdevs | `admin-site/` | Engine console: costs, phases, TaskObserver, ROI, reader feedback |

> Live image regen / OmniRoute scripting still run on your laptop (`python scripts/run_dashboard.py`).  
> Vercel admin is a **shareable read-only console** for the engine itself.

---

## One-time: Vercel + Upstash

```bash
npx vercel login
```

Create **two** Vercel projects (recommended names):

1. `comicengine-reader` ← deploy from `feedback-beta/`
2. `comicengine-admin` ← deploy from `admin-site/`

For the **reader**, add Upstash Redis (Vercel → Storage → Upstash).  
Optionally attach the **same** Upstash to admin so Live feedback works.

Shared env suggestions:

| Env | Reader | Admin |
|-----|--------|-------|
| `KV_REST_API_URL` / `KV_REST_API_TOKEN` (or `UPSTASH_*`) | required | optional (live feedback) |
| `FEEDBACK_ADMIN_SECRET` | required (admin-list API) | — |
| `ADMIN_SITE_PASSWORD` | — | optional gate for fellowdevs |

---

## 1) Deploy Reader (customers)

```bash
# from repo root — refresh comics into feedback-beta/public/comics
PYTHONPATH=src python scripts/prepare_feedback_beta.py

cd feedback-beta
npm install
npx vercel link      # select / create comicengine-reader
npx vercel env pull  # after Upstash is connected
npx vercel --prod
```

In Vercel project settings, set `FEEDBACK_ADMIN_SECRET`.

Send testers **only** the reader URL (e.g. `https://comicengine-reader.vercel.app`).

---

## 2) Deploy Admin (fellowdevs)

```bash
# from repo root — snapshot usage / ROI / tasks / local feedback into admin-site/public/data
PYTHONPATH=src python scripts/prepare_admin_site.py

cd admin-site
npm install
npx vercel link      # select / create comicengine-admin
npx vercel --prod
```

Optional (recommended when sharing outside yourself):

```bash
npx vercel env add ADMIN_SITE_PASSWORD
# also add same Upstash vars as reader for “Refresh live feedback”
```

Send fellowdevs the **admin** URL + password.  
Re-run `prepare_admin_site.py` + redeploy whenever you want fresher cost/phase snapshots.

---

## What each person gets

### Fellowdev (admin URL)
- Total spend, calls, tokens, errors  
- Spend by phase (Phases 6+ often $0 local)  
- TaskObserver status  
- ROI unit economics  
- Reader feedback (snapshot + live Upstash if connected)  
- GitHub link + notes (OmniRoute = text only; images = direct `.env`)

### Customer / tester (reader URL)
- Register / login  
- Stories + panel ratings + overall story feedback  
- No costs / tasks / ROI

---

## Local (still the full power tool)

```bash
# Full admin with live SQLite + curation + media
BETA_REQUIRE_LOGIN=0 python scripts/run_dashboard.py
# → http://127.0.0.1:8765/admin
# → http://127.0.0.1:8765/review  (local reader without Vercel auth)
```

---

## Render Dockerfile (optional fallback)

`Dockerfile` + `render.yaml` remain if you later want a full Python admin on Render.  
Default path for sharing now: **both sites on Vercel** as above.
