# Your site

A static, 8-page personal site (home + 7 sections) built to stand in for a LinkedIn profile. No build step — open `index.html` in a browser, or drag the whole `website` folder onto Netlify Drop / GitHub Pages / Railway's static site deploy to put it online.

## What to fill in

Everything marked with a `[bracketed placeholder]` or an orange **placeholder — ...** tag needs your real content. Quick map:

| Page | File | What to edit |
|---|---|---|
| Home | `index.html` | Elevator pitch, 4 highlight bullets, hero image |
| Biography | `biography.html` | LinkedIn summary + 3 special callouts |
| Education | `education.html` | Schools, degrees, "what I learned" per stop |
| AI Journey | `ai-journey.html` + `js/ai-journey.js` | Story text, your GitHub username, Railway project list |
| Books | `js/books.js` | Title, author, cover image path, summary, rating |
| Musings | `js/musings.js` | Your opinions — no dates by design, keep them evergreen |
| Art | `js/art.js` | Piece titles, image paths, summaries |
| Hiking | `js/hiking.js` | Stats + trip log |

## Images

Drop your photos into these folders and point the matching JS/HTML file at them:
- `images/hero.jpg` — used in the home page hero (swap the placeholder `<div>` for an `<img>`, or set it as a CSS background)
- `images/books/` — book cover photos, referenced from `js/books.js` (`cover` field)
- `images/art/` — your artwork, referenced from `js/art.js` (`image` field)
- `images/hiking/` — trail photos, referenced from `js/hiking.js` (swap `trail-photo` gradient for a background image)

## AI Journey — live GitHub data

`js/ai-journey.js` fetches your public repos straight from the GitHub API at page load, once you set:

```js
const GITHUB_USERNAME = "your-github-username";
```

Your Railway-hosted projects are listed separately in the same file (`RAILWAY_PROJECTS`) since the API can't tell which repos are deployed there — add each one manually with its live URL.

## Deploying

Any static host works since there's no backend: Railway (static site), Netlify, Vercel, or GitHub Pages. Just upload the whole `website` folder.
