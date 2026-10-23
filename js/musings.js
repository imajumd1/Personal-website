let MUSINGS = [];
let ALL_MUSINGS = [];

function musingTeaser(m) {
  if (m.thesis) return m.thesis;
  const plain = htmlToPlainText(m.body || "");
  if (!plain) return "";
  return plain.length > 140 ? plain.slice(0, 140) + "…" : plain;
}

function musingSlug(m) {
  if (m?.slug) return String(m.slug).trim();
  return String(m?.title || "")
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function musingDeepLinkParam() {
  const params = new URLSearchParams(location.search);
  const q = params.get("musing") || params.get("article");
  if (q) return q.trim();
  const hash = (location.hash || "").slice(1).trim();
  if (!hash) return "";
  return hash.replace(/^(musing-|article-)/i, "");
}

function findMusingIndex(list, key) {
  if (!key || !list?.length) return -1;
  const raw = String(key).trim();
  const asNum = Number(raw);
  if (/^\d+$/.test(raw) && asNum >= 0 && asNum < list.length) return asNum;
  const needle = raw.toLowerCase();
  const bySlug = list.findIndex(m => musingSlug(m) === needle);
  if (bySlug >= 0) return bySlug;
  return list.findIndex(m => String(m.title || "").toLowerCase() === needle);
}

function setMusingHash(m) {
  const slug = musingSlug(m);
  if (!slug) return;
  const next = `#${slug}`;
  if (location.hash !== next) {
    history.replaceState(null, "", `${location.pathname}${location.search}${next}`);
  }
}

function clearMusingHash() {
  if (!location.hash) return;
  history.replaceState(null, "", `${location.pathname}${location.search}`);
}

/** Safe same-origin return path when opened from Beliefs (or ?return=…). */
function musingReturnTarget() {
  const params = new URLSearchParams(location.search);
  const from = (params.get("from") || "").trim().toLowerCase();
  if (from === "beliefs") return "biography.html#beliefs";
  const ret = (params.get("return") || "").trim();
  if (!ret) return null;
  try {
    const u = new URL(ret, location.href);
    if (u.origin !== location.origin) return null;
    const path = u.pathname.split("/").pop() || u.pathname;
    if (!/^[a-z0-9._-]+\.html$/i.test(path)) return null;
    return `${path}${u.search}${u.hash}`;
  } catch {
    return null;
  }
}

function leaveMusingToSource() {
  // New tab from Beliefs: close so the Beliefs tab remains underneath.
  if (window.opener && !window.opener.closed) {
    window.close();
  }
  const dest = musingReturnTarget();
  if (dest) {
    location.assign(dest);
  }
}

function openMusing(i, { fromDeepLink = false } = {}) {
  // Index is always against ALL_MUSINGS so deep links work under any tag filter.
  const article = ALL_MUSINGS[i];
  if (!article) return;
  const lb = document.getElementById("musing-lightbox");
  document.getElementById("musing-lightbox-tag").textContent = article.category || article.tag || "";
  document.getElementById("musing-lightbox-title").textContent = article.title || "";
  const meta = document.getElementById("musing-lightbox-meta");
  const bits = [];
  if (article.readingTime) bits.push(`<span>${escapeHtml(article.readingTime)}</span>`);
  meta.innerHTML = bits.join("");
  const body = document.getElementById("musing-lightbox-body");
  body.classList.add("rich-text");
  body.innerHTML = richHtml(article.body);
  lb.hidden = false;
  lb.classList.add("open");
  document.body.style.overflow = "hidden";
  setMusingHash(article);
  document.getElementById("musing-lightbox-close")?.focus();
  if (fromDeepLink) {
    const slug = musingSlug(article);
    const tile = slug
      ? document.querySelector(`.musing-tile[data-slug="${slug.replace(/"/g, "")}"]`)
      : null;
    tile?.scrollIntoView({ block: "nearest" });
  }
}

function closeMusing() {
  const lb = document.getElementById("musing-lightbox");
  if (!lb) return;
  const wasOpen = !lb.hidden || lb.classList.contains("open");
  lb.classList.remove("open");
  lb.hidden = true;
  document.body.style.overflow = "";
  clearMusingHash();
  if (wasOpen) leaveMusingToSource();
}

function openMusingFromUrl() {
  const key = musingDeepLinkParam();
  if (!key) return false;
  const idx = findMusingIndex(ALL_MUSINGS, key);
  if (idx < 0) return false;
  openMusing(idx, { fromDeepLink: true });
  return true;
}

document.addEventListener("DOMContentLoaded", async () => {
  try {
    const content = await loadContent();
    await bootChrome(content);
    const page = content.musings || {};
    applyPageHero(page);

    let items = pageItems(page).map(m => ({
      ...m,
      category: m.category || ({
        tech: "AI & Enterprise Transformation",
        leadership: "Leadership & Organizations",
        life: "Data & Platforms"
      }[m.tag] || "AI & Enterprise Transformation")
    }));
    ALL_MUSINGS = items;
    let activeTag = "all";

    function renderMusings() {
      const list = document.getElementById("musings-list");
      if (!list) return;
      const filtered = activeTag === "all"
        ? items
        : items.filter(m => m.category === activeTag || m.tag === activeTag);
      MUSINGS = filtered;
      list.innerHTML = filtered.map((m, i) => {
        const teaser = musingTeaser(m);
        const slug = musingSlug(m);
        return `
        <article class="musing-tile" data-index="${i}" data-slug="${escapeHtml(slug)}" tabindex="0" role="button" aria-label="Read ${escapeHtml(m.title || "article")}">
          <span class="tag">${escapeHtml(m.category || m.tag || "")}</span>
          <h3>${escapeHtml(m.title)}</h3>
          ${teaser ? `<p class="musing-teaser">${escapeHtml(teaser)}</p>` : ""}
          <div class="perspective-meta musing-tile-meta">
            ${m.readingTime ? `<span>${escapeHtml(m.readingTime)}</span>` : ""}
          </div>
          <span class="musing-tile-cta">Read more</span>
        </article>
      `;
      }).join("") || `<p style="color:var(--ink-soft); grid-column:1/-1;">No perspectives in this category yet.</p>`;

      list.querySelectorAll(".musing-tile").forEach(tile => {
        const open = () => {
          const slug = tile.dataset.slug;
          const fullIdx = findMusingIndex(ALL_MUSINGS, slug);
          openMusing(fullIdx >= 0 ? fullIdx : Number(tile.dataset.index));
        };
        tile.addEventListener("click", open);
        tile.addEventListener("keydown", e => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            open();
          }
        });
      });
    }

    renderMusings();
    openMusingFromUrl();

    window.addEventListener("hashchange", () => {
      if (!musingDeepLinkParam()) {
        closeMusing();
        return;
      }
      openMusingFromUrl();
    });

    document.querySelectorAll(".tag-filter").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".tag-filter").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        activeTag = btn.dataset.tag;
        renderMusings();
      });
    });

    document.getElementById("musing-lightbox-close")?.addEventListener("click", closeMusing);
    document.getElementById("musing-lightbox")?.addEventListener("click", e => {
      if (e.target.id === "musing-lightbox") closeMusing();
    });
    document.addEventListener("keydown", e => {
      if (e.key === "Escape") closeMusing();
    });
  } catch (err) {
    console.error(err);
  }
});
