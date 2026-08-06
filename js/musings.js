document.addEventListener("DOMContentLoaded", async () => {
  try {
    const content = await loadContent();
    await bootChrome(content);
    const page = content.musings || {};
    applyPageHero(page);

    let MUSINGS = pageItems(page);
    let activeTag = "all";

    function renderMusings() {
      const list = document.getElementById("musings-list");
      if (!list) return;
      const filtered = activeTag === "all" ? MUSINGS : MUSINGS.filter(m => m.tag === activeTag);
      list.innerHTML = filtered.map(m => `
        <div class="musing-card reveal in">
          <span class="tag">${escapeHtml(m.tag)}</span>
          <h3>${escapeHtml(m.title)}</h3>
          <div class="rich-text">${richHtml(m.body)}</div>
        </div>
      `).join("") || `<p style="color:var(--ink-soft);">No musings in this category yet.</p>`;
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

    document.getElementById("shuffle-btn")?.addEventListener("click", () => {
      for (let i = MUSINGS.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [MUSINGS[i], MUSINGS[j]] = [MUSINGS[j], MUSINGS[i]];
      }
      renderMusings();
    });
  } catch (err) {
    console.error(err);
  }
});
