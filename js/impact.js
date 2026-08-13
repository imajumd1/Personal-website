document.addEventListener("DOMContentLoaded", async () => {
  try {
    const content = await loadContent();
    await bootChrome(content);
    const page = content.impact || {};
    applyPageHero(page);
    const items = page.items || content.home?.selectedImpact || [];
    const el = document.getElementById("impact-grid");
    if (!el) return;
    el.innerHTML = items.map(item => {
      const media = item.image
        ? `<div class="impact-media" style="background-image:url('${escapeHtml(item.image)}')" role="img" aria-label="${escapeHtml(item.title || item.org || "Case study")}"></div>`
        : "";
      return `
      <article class="impact-card reveal in">
        ${media}
        <div class="impact-body">
          <span class="tag">${escapeHtml(item.org || "")}</span>
          <h3>${escapeHtml(item.title || "")}</h3>
          <dl class="impact-dl">
            <div><dt>Challenge</dt><dd>${escapeHtml(item.challenge || "")}</dd></div>
            <div><dt>Built</dt><dd>${escapeHtml(item.action || "")}</dd></div>
            <div><dt>Impact</dt><dd>${escapeHtml(item.impact || "")}</dd></div>
          </dl>
        </div>
      </article>
    `;
    }).join("") || `<p style="color:var(--ink-soft);">Impact stories coming soon.</p>`;
  } catch (err) {
    console.error(err);
  }
});
