# Scope — Ishita Personal Website

## Goals

- Present Ishita Majumdar as a clear personal brand (**Ishita**) across work, learning, and life interests — not a generic resume dump.
- Replace or complement a LinkedIn-style presence with owned pages: story, education, AI work, reading, opinions, art, and hiking.
- Let Ishita update copy and media without editing HTML by hand, via a simple authenticated admin CMS.
- Stay deployable as a single Python process (e.g. Railway) with content in one JSON file.

## In scope

### Public pages

- **Home** — brand, elevator pitch, hero image, pillar cards (image + expandable text / slides).
- **Biography** — narrative summary and callouts.
- **Education** — schools / programs and what was learned.
- **AI Journey** — journey copy, listed projects (e.g. Railway), and **My Git Projects** (curated cards: image, summary, GitHub link).
- **Books** — titles with covers and summaries.
- **Musings (“My $0.02”)** — evergreen opinion pieces (no dated blog feed required).
- **Art** — gallery of pieces with captions.
- **Hiking** — trail stats / trip entries with photos.

### Product features

- Sticky multi-page navigation and responsive layouts.
- Theme palette switcher (default slate + alternate themes).
- Content API backed by `data/content.json`.
- Email + password admin login with signed cookie sessions.
- Admin panels per section, including editable page titles / eyebrows / ledes where modeled in JSON.
- Image (and selected document) uploads into allowed `images/` folders.
- Rich text editing for appropriate fields in admin.
- Local run via `python3 server.py`; production via `Procfile` + env vars.

### Content sources

- Primary: `data/content.json` (CMS and runtime).
- Media: `images/` (including `images/projects/` for Git project cards).
- Optional hand edits to HTML/JS only for structure or new UI — day-to-day copy is CMS-driven.

## Out of scope / non-goals

- Full user accounts, multi-admin RBAC, or OAuth social login.
- Public comments, newsletter signup backend, or contact-form mailer (unless added later).
- Automatic sync of all GitHub repos as the main “My Git Projects” experience (curated list is intentional; live GitHub API listing is secondary/optional if present).
- Headless CMS SaaS, database, or React/Next build pipeline.
- E-commerce, booking, or blog CMS with taxonomy/tags/archives.
- Native mobile apps.
- Guaranteeing SEO/marketing automation beyond sensible static titles and structure.
- Committing secrets (`data/.secret_key`, `.env`, production passwords).

## Success criteria

- All eight public sections render from shared content and look coherent on desktop and mobile.
- Admin can change pillars, Git projects, and page chrome without redeploying code (redeploy only needed if hosting does not persist `content.json` writes — plan hosting accordingly).
- Login required for admin mutations; public read of content remains open.
