document.addEventListener("DOMContentLoaded", async () => {
  try {
    const content = await loadContent();
    await bootChrome(content);
    const b = content.biography || {};
    applyPageHero(b);

    const quoteEl = document.getElementById("bio-quote");
    if (quoteEl) {
      const quote = (b.quote || "").trim()
        || "Technology creates value only when people can trust it, use it, and act on it";
      quoteEl.innerHTML = `<p>${escapeHtml(quote)}</p>`;
    }

    const about = document.getElementById("bio-about");
    if (about) {
      const html = b.summary || b.bios?.full || "";
      about.innerHTML = richHtml(html) || `<p style="color:var(--ink-soft);">About coming soon.</p>`;
    }

    const builder = document.getElementById("bio-builder");
    if (builder) {
      builder.innerHTML = richHtml(b.builder || "")
        || `<p style="color:var(--ink-soft);">Builder notes coming soon.</p>`;
    }

    const bios = b.bios || {};
    const actions = document.getElementById("bio-actions");
    if (actions) {
      const parts = [];
      if (b.headshot) {
        parts.push(`<a class="btn btn-ghost btn-small" href="${escapeHtml(b.headshot)}" target="_blank" rel="noopener">View headshot</a>`);
      }
      if (b.bioDownload) {
        parts.push(`<a class="btn btn-ghost btn-small" href="${escapeHtml(b.bioDownload)}" target="_blank" rel="noopener">Download bio</a>`);
      }
      if (bios.short) {
        parts.push(`<button type="button" class="btn btn-ghost btn-small" id="copy-short-bio">Copy 50-word bio</button>`);
      }
      actions.innerHTML = parts.join("");
      document.getElementById("copy-short-bio")?.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(bios.short || "");
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
      }).join("") || `<p style="color:var(--ink-soft);">Career timeline coming soon.</p>`;
    }

    const callouts = document.getElementById("bio-callouts");
    if (callouts) {
      const items = Array.isArray(b.recognition) && b.recognition.length
        ? b.recognition
        : (b.callouts || []);
      callouts.innerHTML = items.map(item => `
        <article class="recognition-item">
          <h3>${escapeHtml(item.title)}</h3>
          <div class="rich-text">${richHtml(item.text)}</div>
        </article>
      `).join("") || `<p style="color:var(--ink-soft);">Recognition coming soon.</p>`;
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

    const subnav = document.querySelector(".bio-subnav");
    if (subnav) {
      const links = [...subnav.querySelectorAll("a[href^='#']")];
      const sections = links
        .map(a => document.querySelector(a.getAttribute("href")))
        .filter(Boolean);

      const setActive = () => {
        const y = window.scrollY + 120;
        let current = sections[0];
        for (const section of sections) {
          if (section.offsetTop <= y) current = section;
        }
        links.forEach(a => {
          a.classList.toggle("active", current && a.getAttribute("href") === `#${current.id}`);
        });
      };
      setActive();
      window.addEventListener("scroll", setActive, { passive: true });
    }
  } catch (err) {
    console.error(err);
  }
});
