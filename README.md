# Ishita — Personal Website

Personal site for **Ishita Majumdar** (brand: **Ishita**). Multi-page static HTML/CSS/JS with a small Python CMS so content lives in `data/content.json` and can be edited through an authenticated admin UI.

**Repo:** [github.com/imajumd1/Personal-website](https://github.com/imajumd1/Personal-website)

## Pages

| Page | File | Notes |
|------|------|--------|
| Home | `index.html` | Elevator pitch, hero photo, pillar cards |
| Biography | `biography.html` | Summary and callouts |
| Education | `education.html` | Schools / learning stops |
| AI Journey | `ai-journey.html` | Story, Railway projects, **My Git Projects** cards |
| Books | `books.html` | Reading list with flip cards |
| My $0.02 | `musings.html` | Evergreen opinions (no dates by design) |
| Art | `art.html` | Artwork gallery |
| Hiking | `hiking.html` | Trails and trip log |
| Roma | `roma.html` | Flight-search agent: chat or form, buy/wait recommendation |
| Admin | `admin.html` | CMS (login required) |
| Login | `login.html` | Email + password gate |

## Stack

- Static front end: HTML, `css/style.css`, page scripts under `js/`
- Backend: `server.py` — `ThreadingHTTPServer` serving static files plus:
  - `GET/POST /api/content` — read/write `data/content.json`
  - `POST /api/login`, `POST /api/logout`, `GET /api/session`
  - `POST /api/upload` — images/docs into `images/{folder}/`
  - `/api/roma/*` — the Roma flight agent (search, chat, airports, airlines, status)
- No Node build step; Python 3 stdlib only

## Run locally

```bash
cd website   # this folder
python3 server.py
```

Open:

- Site: http://127.0.0.1:8080/
- Admin login: http://127.0.0.1:8080/login.html

Default local credentials (override with env vars):

| Variable | Default (local) | Purpose |
|----------|-----------------|---------|
| `PORT` | `8080` | HTTP port |
| `HOST` | `0.0.0.0` | Bind address |
| `ADMIN_EMAIL` | `imajumd1@gmail.com` | Allowed admin email |
| `ADMIN_PASSWORD` | `local-dev-only` | Admin password |
| `SECRET_KEY` | auto-generated into `data/.secret_key` | Session signing |

`data/.secret_key` is gitignored. Set `SECRET_KEY` explicitly in production.

## Editing content

1. Sign in at `/login.html`, then open `/admin.html`.
2. Edit sections (home pillars, page titles/eyebrows/ledes, books, art, hiking, AI Journey story, Git projects, etc.).
3. Use the rich text editor where available; upload images into allowed folders (`hero`, `books`, `art`, `hiking`, `pillars`, `roles`, `projects`).
4. Save — writes `data/content.json`. Public pages load that JSON via `/api/content`.

You can also edit `data/content.json` by hand while the server is stopped (or carefully while running).

### My Git Projects

On AI Journey, curated cards (`aiJourney.gitProjects`) show image, summary, and repo URL. Manage them in Admin → AI Journey. Thumbnails live under `images/projects/`.

## Roma — flight search agent

`roma.html` is a flight-search agent you can talk to or fill in a form for. It returns
fares, explains whether to buy now or wait (with the rule that produced the verdict, the
dollars at stake, and a revisit date), and deep-links the same search to Kayak, Google
Flights, Expedia, and Priceline rather than scraping them.

**Fares are simulated demonstration data, not live quotes** — labelled on the page, on every
result, and in the API response. Optional environment variables turn on a real Amadeus
source (`AMADEUS_CLIENT_ID` / `AMADEUS_CLIENT_SECRET`) and an LLM for parsing and phrasing
(`ROMA_LLM_PROVIDER` plus a provider key); with none set, Roma runs fully offline on local
heuristics, and a model can never author a price or a verdict.

Details, API shapes, and the guarantees: [`roma/README.md`](roma/README.md).

## Theme

Visitors can switch palettes (default slate, ink, copper, forest) via the theme control; preference is stored in the browser. See `design.md`.

## Deploy (Railway)

`Procfile`:

```
web: python3 server.py
```

Copy `railway.env.example` → set real values on Railway (do not commit secrets):

```
ADMIN_EMAIL=...
ADMIN_PASSWORD=...   # strong password
SECRET_KEY=...       # long random string
PORT=8080
```

Railway injects `PORT`; the server reads it. After deploy, log into `/login.html` with your production admin credentials.

Other hosts that can run a Python web process work the same way. Pure static hosting alone is not enough if you need the CMS/API.

## Project layout

```
├── index.html, *.html     # pages
├── css/style.css          # public design system
├── css/admin.css          # admin UI
├── js/                    # page + admin + richtext scripts
├── images/                # media (hero, pillars, projects, …)
├── data/content.json      # CMS source of truth
├── roma/                  # Roma flight agent (stdlib only) — see roma/README.md
├── server.py              # static + API + auth
├── Procfile               # Railway
├── railway.env.example
├── scope.md               # product scope
└── design.md              # visual / UX notes
```

## License / use

Personal portfolio site — content and branding are Ishita’s.
