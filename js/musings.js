let MUSINGS = [];

function musingTeaser(m) {
  if (m.thesis) return m.thesis;
  const plain = htmlToPlainText(m.body || "");
  if (!plain) return "";
  return plain.length > 140 ? plain.slice(0, 140) + "…" : plain;
}

function openMusing(i) {
  const m = MUSINGS[i];
  if (!m) return;
  const lb = document.getElementById("musing-lightbox");
  document.getElementById("musing-lightbox-tag").textContent = m.category || m.tag || "";
  document.getElementById("musing-lightbox-title").textContent = m.title || "";
  const meta = document.getElementById("musing-lightbox-meta");
  const bits = [];
  if (m.readingTime) bits.push(`<span>${escapeHtml(m.readingTime)}</span>`);
  meta.innerHTML = bits.join("");
  const body = document.getElementById("musing-lightbox-body");
  body.classList.add("rich-text");
  body.innerHTML = richHtml(m.body);
  lb.hidden = false;
  lb.classList.add("open");
  document.body.style.overflow = "hidden";
  document.getElementById("musing-lightbox-close")?.focus();
}

function closeMusing() {
  const lb = document.getElementById("musing-lightbox");
  if (!lb) return;
  lb.classList.remove("open");
  lb.hidden = true;
  document.body.style.overflow = "";
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
        return `
        <article class="musing-tile" data-index="${i}" tabindex="0" role="button" aria-label="Read ${escapeHtml(m.title || "article")}">
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
        const open = () => openMusing(Number(tile.dataset.index));
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
