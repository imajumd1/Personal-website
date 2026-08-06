document.addEventListener("DOMContentLoaded", async () => {
  try {
    const content = await loadContent();
    await bootChrome(content);
    const b = content.biography;
    applyPageHero(b);

    const summary = document.getElementById("bio-summary");
    if (summary) {
      summary.classList.add("rich-text");
      summary.innerHTML = richHtml(b.summary || "");
    }

    const career = document.getElementById("bio-career");
    if (career) {
      career.innerHTML = (b.career || []).map(item => {
        const attachments = Array.isArray(item.attachments) ? item.attachments : [];
        const files = attachments.length
          ? `<div class="role-files">
              ${attachments.map(f => `
                <a class="role-file" href="${escapeHtml(f.path)}" target="_blank" rel="noopener">
                  <span class="role-file-type">${escapeHtml(fileIconLabel(f.type || (f.path || "").split(".").pop()))}</span>
                  <span class="role-file-name">${escapeHtml(f.name || f.path)}</span>
                </a>
              `).join("")}
            </div>`
          : "";
        return `
          <div class="timeline-item">
            <h3>${escapeHtml(item.title)}</h3>
            <div class="meta">${escapeHtml(item.meta)}</div>
            <div class="rich-text">${richHtml(item.text)}</div>
            ${files}
          </div>
        `;
      }).join("");
    }

    const callouts = document.getElementById("bio-callouts");
    if (callouts) {
      callouts.innerHTML = (b.callouts || []).map(item => `
        <div class="highlight-card">
          <span class="num">★</span>
          <h3>${escapeHtml(item.title)}</h3>
          <div class="rich-text">${richHtml(item.text)}</div>
        </div>
      `).join("");
    }
  } catch (err) {
    console.error(err);
  }
});
