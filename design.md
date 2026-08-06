# Design — Ishita Personal Website

Visual and interaction notes grounded in `css/style.css` and the public HTML pages. Admin styling lives mainly in `css/admin.css`.

## Brand & direction

- Brand name **Ishita** is a primary signal in the sticky nav (serif wordmark), not a tiny eyebrow.
- Mood: calm editorial portfolio — warm off-white paper, dark ink, slate accent — modern minimalist, not neon or generic purple SaaS.
- One composition per viewport on home: pitch + supporting line + CTAs + hero photo; pillars sit below as a second job.

## Color system

CSS variables on `:root` (default **slate**):

| Token | Role | Default |
|-------|------|---------|
| `--ink` / `--ink-soft` | Body text | `#17191f` / `#555a66` |
| `--paper` / `--paper-raised` | Page / raised surfaces | `#f6f5f2` / `#ffffff` |
| `--line` | Borders / rules | `#e3e0d9` |
| `--accent` | Primary accent (slate blue) | `#2f4a6a` |
| `--accent-soft` / `--accent-deep` | Soft fill / deep accent | `#e8eef5` / `#1a2d44` |
| `--accent-2` | Secondary (warm copper) | `#9a6240` |
| `--radius` | Corner radius | `14px` |
| `--max` | Content width | `1080px` |

### Theme switcher

`data-theme` on `<html>` swaps palettes:

- **(default)** slate blue accent on warm paper
- **`ink`** — charcoal accent, cooler gray paper
- **`copper`** — terracotta accent, warmer paper
- **`forest`** — deep green accent

UI: `.theme-switcher` with mono label and pressed-state buttons. Themes recolor accents/paper/lines without separate stylesheets.

## Typography

System stacks (no external font CDN required):

- **Serif** (`--serif`): Iowan Old Style / Palatino / Georgia — brand, headlines, card titles, pitch headline.
- **Sans** (`--sans`): Avenir Next / Segoe UI / Helvetica — body.
- **Mono** (`--mono`): SF Mono / Consolas / Menlo — eyebrows, meta, labels, theme control.

Hierarchy: large serif pitch on home; page heroes use serif `h1` + softer lede; section labels often mono uppercase/small.

## Layout patterns

### Global

- `.wrap` centers content to `--max` with horizontal padding.
- Sticky `.site-nav` with frosted paper background and blur; pill-shaped nav links; active/hover use `--accent-soft`.

### Home hero

- `.hero` / `.hero-columns`: **copy left, photo right** on wide screens; stacks on small screens.
- `.hero-copy`: eyebrow (mono), `h1.pitch-headline` (serif), `.pitch` supporting sentence, `.btn-row` CTAs.
- `.hero-image`: dominant photo plane for the hero (not a small floating card collage).

### Page heroes

- `.page-hero` on inner pages: title + lede only — one job per section header.

### Pillars (home highlights)

- Grid of highlight/pillar items: optional cover image, title, truncated text with expand, optional slide rotation from extra JPEGs.
- Editorial cards with radius and light borders — content-first, not dashboard widgets.

### My Git Projects

- `.git-projects-grid`: responsive columns (3 → 2 → 1).
- `.git-project-card`: media on top (`.git-project-media`), body with serif title, summary, and `.git-project-link` to the repo.
- Hover lifts slightly / border emphasis; keep cards as the interaction container for “open project.”

### Other section patterns

- **Books:** flip cards (front cover / back summary).
- **Art:** tiled gallery with captions.
- **Hiking:** trail rows with photo + meta (mono) + description.
- **Repos / legacy project lists:** `.repo-card` style where used for simpler lists.

## Motion

Intentional, light motion: nav hover, hero image hover, pillar expand, project card hover, theme button pressed state. Prefer short transitions over decorative animation noise.

## Admin UX

- Separate admin chrome (`admin.html` + `admin.css`): tabbed/panel sections for Home, Biography, Education, AI Journey (including Git projects), Books, Musings, Art, Hiking, Site.
- Hints for uploads (e.g. first pillar image = cover; extra files = slideshow).
- Rich text (`js/richtext.js`) for longer copy fields.
- Login gate before CMS; session cookie named for the Ishita admin flow.
- Prefer clear forms and lists over marketing flair — admin is a tool.

## Responsive

- Hero columns collapse; git project grid collapses; nav may use a toggle on narrow viewports.
- Touch targets on pills/buttons stay comfortable; images `max-width: 100%`.

## Do / don’t (for future edits)

- **Do** keep brand-forward home composition and slate-led default palette.
- **Do** reuse existing tokens and component classes.
- **Don’t** introduce purple glow gradients, heavy multi-shadow card stacks, or flat single-purpose dashboards on the public home hero.
- **Don’t** put secondary marketing strips (stats, schedules) into the first home viewport.
