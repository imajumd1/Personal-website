document.addEventListener("DOMContentLoaded", async () => {
  try {
    const content = await loadContent();
    await bootChrome(content);
    const a = content.aiJourney || {};
    const lab = content.aiLab || {};
    applyPageHero({
      eyebrow: lab.eyebrow || a.eyebrow,
      title: lab.title || a.title,
      lede: lab.lede || a.lede
    });

    const story = document.getElementById("ai-story");
    if (story) {
      story.classList.add("rich-text");
      story.innerHTML = richHtml(a.story || "");
    }

    const username = a.githubUsername || content.site?.github || "imajumd1";
    const githubLink = document.getElementById("github-link");
    if (githubLink) githubLink.href = `https://github.com/${username}`;

    const labItems = Array.isArray(lab.items) && lab.items.length
      ? lab.items
      : (Array.isArray(a.featuredBuilds) ? a.featuredBuilds : []).map(p => ({
          name: p.name,
          summary: p.summary,
          image: p.image,
          liveUrl: p.liveUrl,
          repoUrl: "",
          why: "",
          tech: "",
          learned: "",
          bucket: "personal"
        }));

    const defaultBuckets = [
      {
        id: "personal",
        title: "Personal Productivity",
        blurb: "Agents I build for my own life: reclaiming time from noisy chats, shipping small tools I actually use, and learning by putting something live."
      },
      {
        id: "enterprise",
        title: "Enterprise Productivity",
        blurb: "Products I build for enterprise work: HR, decisioning, skills, commerce, and health agents meant to demo clearly and hand off to a real team."
      }
    ];
    const buckets = Array.isArray(lab.buckets) && lab.buckets.length
      ? lab.buckets
      : defaultBuckets;

    // Prefer #lab-buckets; fall back to legacy #lab-grid so a partial deploy never blanks the page.
    const labEl =
      document.getElementById("lab-buckets") ||
      document.getElementById("lab-grid");

    const renderCard = (p) => {
      const media = p.image
        ? `style="background-image:url('${escapeHtml(p.image)}')"`
        : `style="background:linear-gradient(155deg, var(--accent), var(--accent-deep))"`;
      const docs = Array.isArray(p.docs) ? p.docs : [];
      const links = [
        p.liveUrl ? `<a class="btn btn-primary btn-small" href="${escapeHtml(p.liveUrl)}" target="_blank" rel="noopener">Live →</a>` : "",
        p.repoUrl ? `<a class="btn btn-ghost btn-small" href="${escapeHtml(p.repoUrl)}" target="_blank" rel="noopener">GitHub</a>` : ""
      ].filter(Boolean).join("");
      const docLinks = docs.length
        ? `<ul class="lab-docs">${docs.map(d =>
            `<li><a href="${escapeHtml(d.url || "")}" target="_blank" rel="noopener">${escapeHtml(d.label || d.url || "Doc")}</a></li>`
          ).join("")}</ul>`
        : "";
      return `
        <article class="lab-card${docs.length ? " lab-card-docs" : ""}">
          <div class="lab-media" ${media} role="img" aria-label="${escapeHtml(p.name || "Project")}"></div>
          <div class="lab-body">
            <h3>${escapeHtml(p.name || "")}</h3>
            <p class="lab-summary">${escapeHtml(p.summary || "")}</p>
            ${p.why ? `<p><strong>Why</strong>: ${escapeHtml(p.why)}</p>` : ""}
            ${p.tech ? `<p class="lab-meta"><strong>Tech</strong>: ${escapeHtml(p.tech)}</p>` : ""}
            ${p.learned ? `<p><strong>Learned</strong>: ${escapeHtml(p.learned)}</p>` : ""}
            ${docLinks}
            <div class="btn-row">${links}</div>
          </div>
        </article>
      `;
    };

    if (labEl) {
      // Do NOT add class "reveal" on dynamically injected nodes.
      // main.js only observes .reveal at DOMContentLoaded; late nodes would stay opacity:0 forever.
      const usedIds = new Set();
      const sections = buckets.map(bucket => {
        const id = bucket.id || "personal";
        usedIds.add(id);
        const items = labItems.filter(p => (p.bucket || "personal") === id);
        return `
          <section class="lab-bucket" id="bucket-${escapeHtml(id)}">
            <h3 class="lab-bucket-title">${escapeHtml(bucket.title || id)}</h3>
            <p class="lab-bucket-blurb">${escapeHtml(bucket.blurb || "")}</p>
            <div class="lab-grid">
              ${items.map(renderCard).join("") || `<p style="color:var(--ink-soft);">No builds in this section yet.</p>`}
            </div>
          </section>
        `;
      });

      const orphan = labItems.filter(p => !usedIds.has(p.bucket || "personal"));
      if (orphan.length) {
        sections.push(`
          <section class="lab-bucket">
            <h3 class="lab-bucket-title">More builds</h3>
            <div class="lab-grid">${orphan.map(renderCard).join("")}</div>
          </section>
        `);
      }

      if (!Array.isArray(lab.buckets) || !lab.buckets.length) {
        const hasBucketFields = labItems.some(p => p.bucket);
        if (!hasBucketFields && labEl.id === "lab-grid") {
          labEl.innerHTML = labItems.map(renderCard).join("") ||
            `<p style="color:var(--ink-soft);">No Building with AI items yet.</p>`;
        } else {
          labEl.innerHTML = sections.join("");
        }
      } else {
        labEl.innerHTML = sections.join("");
      }
    }
  } catch (err) {
    console.error(err);
    const labEl =
      document.getElementById("lab-buckets") ||
      document.getElementById("lab-grid");
    if (labEl && !labEl.innerHTML.trim()) {
      labEl.innerHTML = `<p style="color:var(--ink-soft);">Could not load builds. Refresh and try again.</p>`;
    }
  }
});
