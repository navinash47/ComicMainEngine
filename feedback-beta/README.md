# ComicEngine Reader (Vercel)

Public reader site: **register / login (username + password)**, comics, panel + story ratings.  
No admin stats here.

See [docs/HOSTING.md](../docs/HOSTING.md) for deploy steps.

```bash
PYTHONPATH=src python ../scripts/prepare_feedback_beta.py
npm install
npx vercel --prod
```

Required env (Vercel + Upstash):

- `KV_REST_API_URL` / `KV_REST_API_TOKEN` (or `UPSTASH_REDIS_REST_*`)
- `FEEDBACK_ADMIN_SECRET` — for `/api/admin-list` only
