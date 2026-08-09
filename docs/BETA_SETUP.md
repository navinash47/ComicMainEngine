# ComicEngine beta publish (Phase 10)

Google login + Mom Test feedback need the **FastAPI app**.
Cloudflare Pages/R2 host the static mirror of approved stories.

## 1) Google OAuth (Phase 8.6)

1. Open [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials.
2. Create **OAuth client ID** → Web application.
3. Authorized redirect URIs (examples):
   - `http://127.0.0.1:8765/auth/callback`
   - `https://YOUR_PUBLIC_HOST/auth/callback`
4. Copy Client ID + Secret into project `.env`:

```bash
GOOGLE_OAUTH_CLIENT_ID=....apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=...
SESSION_SECRET=long-random-string
PUBLIC_BASE_URL=http://127.0.0.1:8765
ADMIN_EMAILS=you@gmail.com
BETA_REQUIRE_LOGIN=1
AUTH_DEV_BYPASS=0
```

Local-only without Google yet:

```bash
AUTH_DEV_BYPASS=1
ADMIN_EMAILS=dev@local.test
```

Then open `/login` → **Dev login**.

## 2) Reviewer flow

1. Sign in with Google.
2. Read stories in `/library` and `/stories/{id}`.
3. Submit **Mom Test** questionnaire at `/feedback`.
4. Admins (`ADMIN_EMAILS`) use `/reviewers` to read/export logs for Version 2.

Export CLI:

```bash
PYTHONPATH=src python scripts/phase8_6_feedback.py export-file
```

## 3) Cloudflare Pages + R2 (Phase 10)

```bash
# Build static package
PYTHONPATH=src python scripts/phase10_publish.py export

# Optional: upload to R2 (needs boto3 + CF_* env)
pip install boto3
# CF_ACCOUNT_ID=...
# CF_R2_ACCESS_KEY_ID=...
# CF_R2_SECRET_ACCESS_KEY=...
# CF_R2_BUCKET=comicengine-beta
PYTHONPATH=src python scripts/phase10_publish.py upload-r2

# Optional: deploy Pages from the site folder
PYTHONPATH=src python scripts/phase10_publish.py deploy-pages
```

For **live Google login on a public URL**, put the FastAPI app behind HTTPS
(Cloudflare Tunnel, Fly, Railway, etc.) and set `PUBLIC_BASE_URL` + OAuth redirect
to that host. Pages alone is a media/reader mirror.

Example tunnel:

```bash
DASHBOARD_HOST=0.0.0.0 python scripts/run_dashboard.py
cloudflared tunnel --url http://127.0.0.1:8765
# Then set PUBLIC_BASE_URL to the https://*.trycloudflare.com URL and update Google redirect.
```

## 4) Phase 11 + Version 2

```bash
PYTHONPATH=src python scripts/phase11_cost_guardrails.py gate
```

After Phase 11, new product work is **Version 2** starting at **Phase 12**, driven by Mom Test exports.
