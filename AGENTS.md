# AGENTS.md

## Cursor Cloud specific instructions

This repository contains two independent Python 3 (stdlib-only) apps. Both need
**no dependencies, no virtualenv, and no build step** — the VM already has a
compatible Python 3 (`.python-version` pins 3.12). There is no package manager,
lockfile, or `requirements.txt`, so the startup update script is a no-op check.

### Services

| Service | Dir | Run (dev) | URL | Notes |
|---------|-----|-----------|-----|-------|
| Personal website + CMS | repo root | `python3 server.py` | http://127.0.0.1:8080/ | Static pages + content API + email-gated admin. Binds `0.0.0.0:8080`. |
| Roma flight-search agent | `roma/` | `cd roma && python3 run.py` | http://127.0.0.1:8787/ | Standalone; binds `127.0.0.1:8787` (localhost only). |

The two apps are fully separate — Roma is not mounted by the site. Run each in
its own terminal/process.

### Personal website

- Admin login lives at `/login.html`; defaults are `ADMIN_EMAIL=imajumd1@gmail.com`
  / `ADMIN_PASSWORD=local-dev-only` (override via env vars). Content is stored in
  `data/content.json` and served via `GET /api/content`; admin edits `PUT` it back.
- `data/.secret_key` is auto-generated on first run and is gitignored.

### Roma (`roma/`)

- Tests: `cd roma && python3 -m unittest discover` (89 tests, stdlib only, no network).
- CLI search goes through the same engine as the web UI, e.g.
  `python3 run.py search --from BOS --to MIA --depart 2026-11-03 --return 2026-11-10`.
- Fares are **simulated** by Roma's own deterministic model — not real prices.
- Port override order: `--port` > `ROMA_PORT` > `PORT` (default `8787`).
- Runtime state (`roma/data/price_history.sqlite3`) is generated on demand and
  gitignored; deleting it just resets modelled price history.
- Optional external seams (all off by default): Amadeus live fares
  (`AMADEUS_CLIENT_ID`/`AMADEUS_CLIENT_SECRET`) and an OpenAI-compatible phrasing
  model (`ROMA_LLM_*`). Neither is required or verified against live credentials.

### Lint / test

There is no configured linter and no test suite for the site. Use
`python3 -m compileall server.py` (site) or `python3 -m compileall roma/romacore roma/run.py`
(Roma) for a quick syntax check. Roma's `unittest` suite is the real test signal.
