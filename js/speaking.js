document.addEventListener("DOMContentLoaded", async () => {
  try {
    const content = await loadContent();
    await bootChrome(content);
    const page = content.speaking || {};
    applyPageHero(page);
    const items = page.items || [];
    const el = document.getElementById("speaking-list");
    if (!el) return;
    el.innerHTML = items.map(s => `
      <article class="speaking-card reveal in">
        <h3>${escapeHtml(s.title || "")}</h3>
        <div class="meta">${escapeHtml([s.event, s.meta].filter(Boolean).join(" · "))}</div>
        <p>${escapeHtml(s.blurb || "")}</p>
        ${s.link ? `<p style="margin-top:10px;"><a class="go" href="${escapeHtml(s.link)}" target="_blank" rel="noopener">Details →</a></p>` : ""}
      </article>
    `).join("") || `<p style="color:var(--ink-soft);">Speaking calendar expanding — check back soon.</p>`;
  } catch (err) {
    console.error(err);
  }
});
