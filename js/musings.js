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

    function bindReadMore(list) {
      list.querySelectorAll(".musing-read-more").forEach(btn => {
        btn.addEventListener("click", () => {
          const detail = document.getElementById(btn.getAttribute("aria-controls"));
          if (!detail) return;
          const card = btn.closest(".musing-card");
          const open = detail.hasAttribute("hidden");
          if (open) {
            detail.removeAttribute("hidden");
            btn.setAttribute("aria-expanded", "true");
            btn.textContent = "Show less";
            card?.classList.add("is-expanded");
          } else {
            detail.setAttribute("hidden", "");
            btn.setAttribute("aria-expanded", "false");
            btn.textContent = "Read more";
            card?.classList.remove("is-expanded");
          }
        });
      });
    }

    function renderMusings() {
      const list = document.getElementById("musings-list");
      if (!list) return;
      const filtered = activeTag === "all"
        ? items
        : items.filter(m => m.category === activeTag || m.tag === activeTag);
      list.innerHTML = filtered.map((m, i) => {
        const thesis = m.thesis || htmlToPlainText(m.body || "").slice(0, 160);
        const thesisSuffix = m.thesis ? "" : (thesis ? "…" : "");
        const id = `musing-detail-${i}`;
        return `
        <article class="musing-card reveal in">
          <span class="tag">${escapeHtml(m.category || m.tag || "")}</span>
          <h3>${escapeHtml(m.title)}</h3>
          ${thesis ? `<p class="perspective-thesis musing-teaser">${escapeHtml(thesis)}${thesisSuffix}</p>` : ""}
          <div class="perspective-meta" style="margin:0 0 12px;">
            ${m.readingTime ? `<span>${escapeHtml(m.readingTime)}</span>` : ""}
          </div>
          <button type="button" class="btn btn-ghost btn-small musing-read-more" aria-expanded="false" aria-controls="${id}">
            Read more
          </button>
          <div class="musing-detail" id="${id}" hidden>
            <div class="rich-text">${richHtml(m.body)}</div>
          </div>
        </article>
      `;
      }).join("") || `<p style="color:var(--ink-soft);">No perspectives in this category yet.</p>`;
      bindReadMore(list);
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
  } catch (err) {
    console.error(err);
  }
});
