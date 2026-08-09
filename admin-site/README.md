# ComicEngine Admin (Vercel)

Read-only engine console for **you + fellowdevs**: costs, phases, tasks, ROI, reader feedback.

```bash
PYTHONPATH=src python ../scripts/prepare_admin_site.py
npm install
npx vercel --prod
```

Optional env:

- `ADMIN_SITE_PASSWORD` — simple gate when sharing the URL
- Same Upstash as reader — enables **Refresh live feedback**

See [docs/HOSTING.md](../docs/HOSTING.md).
