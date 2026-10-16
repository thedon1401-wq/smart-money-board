# Smart Money Board (local prototype)
- `python3 fetch.py`  → pulls real data (data-api /v1/leaderboard, /positions, /activity; gamma /markets) into data/data.json (~10s)
- `python3 build.py`  → static site in site/ (index.html, style.css, data.json)
- `./refresh.sh`      → both; run on a schedule (cron / GitHub Actions)
- Preview: `cd site && python3 -m http.server 8765`
- Placeholders: search for PLACEHOLDER (sponsor banners, affiliate link `AFF` in build.py, sponsor email).
- Env: POOL (wallets tracked, default 50), MIN_POS (min $ position, default 500).

## Deploy (GitHub Pages)
`.github/workflows/refresh-deploy.yml` runs every 3h, on push to main, and manually: fetch → build → commit dated snapshot to `data/history/` → deploy `site/` to Pages.
One-time: repo Settings → Pages → Source = **GitHub Actions**.
