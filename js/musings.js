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
      list.innerHTML = filtered.map(m => {
        const thesis = m.thesis || htmlToPlainText(m.body || "").slice(0, 160);
        return `
        <article class="musing-card reveal in">
          <span class="tag">${escapeHtml(m.category || m.tag || "")}</span>
          <h3>${escapeHtml(m.title)}</h3>
          ${thesis ? `<p class="perspective-thesis">${escapeHtml(thesis)}${m.thesis ? "" : "…"}</p>` : ""}
          <div class="perspective-meta" style="margin:0 0 12px;">
            ${m.readingTime ? `<span>${escapeHtml(m.readingTime)}</span>` : ""}
            ${m.date ? `<span>${escapeHtml(m.date)}</span>` : ""}
          </div>
          <div class="rich-text">${richHtml(m.body)}</div>
        </article>
      `;
      }).join("") || `<p style="color:var(--ink-soft);">No perspectives in this category yet.</p>`;
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
