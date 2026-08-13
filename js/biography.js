document.addEventListener("DOMContentLoaded", async () => {
  try {
    const content = await loadContent();
    await bootChrome(content);
    const b = content.biography || {};
    applyPageHero(b);

    const bios = b.bios || {};
    const lengths = document.getElementById("bio-lengths");
    if (lengths) {
      const blocks = [
        { key: "short", label: "50-word bio", text: bios.short },
        { key: "medium", label: "150-word bio", text: bios.medium },
        { key: "full", label: "Full executive biography", text: bios.full || b.summary }
      ].filter(x => x.text);
      lengths.innerHTML = blocks.map(block => {
        const isHtml = /<[a-z][\s\S]*>/i.test(String(block.text));
        const body = isHtml
          ? `<div class="rich-text">${richHtml(block.text)}</div>`
          : `<p>${escapeHtml(block.text)}</p>`;
        const words = htmlToPlainText(isHtml ? block.text : `<p>${block.text}</p>`).split(/\s+/).filter(Boolean).length;
        return `
          <section class="bio-length reveal in" id="bio-${block.key}">
            <div class="meta">${escapeHtml(block.label)} · ~${words} words</div>
            <h2>${escapeHtml(block.label)}</h2>
            ${body}
          </section>
        `;
      }).join("");
    }

    const actions = document.getElementById("bio-actions");
    if (actions) {
      const parts = [];
      if (b.headshot) {
        parts.push(`<a class="btn btn-ghost btn-small" href="${escapeHtml(b.headshot)}" target="_blank" rel="noopener">View headshot</a>`);
      }
      if (b.bioDownload) {
        parts.push(`<a class="btn btn-ghost btn-small" href="${escapeHtml(b.bioDownload)}" target="_blank" rel="noopener">Download bio</a>`);
      }
      parts.push(`<button type="button" class="btn btn-ghost btn-small" id="copy-short-bio">Copy 50-word bio</button>`);
      actions.innerHTML = parts.join("");
      document.getElementById("copy-short-bio")?.addEventListener("click", async () => {
        const text = bios.short || "";
        try {
          await navigator.clipboard.writeText(text);
          const btn = document.getElementById("copy-short-bio");
          if (btn) btn.textContent = "Copied";
        } catch (_) {}
      });
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

    const beliefs = document.getElementById("beliefs-grid");
    if (beliefs) {
      const items = content.home?.beliefs || [];
      beliefs.innerHTML = items.map(item => `
        <article class="belief-card reveal in">
          <h3>${escapeHtml(item.title || "")}</h3>
          <p>${escapeHtml(item.text || "")}</p>
          ${item.link ? `<a class="go" href="${escapeHtml(item.link)}">${escapeHtml(item.linkLabel || "Read more")} →</a>` : ""}
        </article>
      `).join("") || `<p style="color:var(--ink-soft);">Beliefs coming soon.</p>`;
    }
  } catch (err) {
    console.error(err);
  }
});
