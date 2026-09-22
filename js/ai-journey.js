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
      : (a.featuredBuilds || []).map(p => ({
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
        blurb: "Agents I build for my own life."
      },
      {
        id: "enterprise",
        title: "Enterprise Productivity",
        blurb: "Products I build for enterprise work."
      }
    ];
    const buckets = Array.isArray(lab.buckets) && lab.buckets.length
      ? lab.buckets
      : defaultBuckets;

    const labEl = document.getElementById("lab-buckets");
    if (labEl) {
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
              ${p.why ? `<p><strong>Why</strong> — ${escapeHtml(p.why)}</p>` : ""}
              ${p.tech ? `<p class="lab-meta"><strong>Tech</strong> — ${escapeHtml(p.tech)}</p>` : ""}
              ${p.learned ? `<p><strong>Learned</strong> — ${escapeHtml(p.learned)}</p>` : ""}
              ${docLinks}
              <div class="btn-row">${links}</div>
            </div>
          </article>
        `;
      };

      const usedIds = new Set();
      labEl.innerHTML = buckets.map(bucket => {
        usedIds.add(bucket.id);
        const items = labItems.filter(p => (p.bucket || "personal") === bucket.id);
        return `
          <section class="lab-bucket reveal" id="bucket-${escapeHtml(bucket.id || "")}">
            <h3 class="lab-bucket-title">${escapeHtml(bucket.title || "")}</h3>
            <p class="lab-bucket-blurb">${escapeHtml(bucket.blurb || "")}</p>
            <div class="lab-grid">
              ${items.map(renderCard).join("") || `<p style="color:var(--ink-soft);">No builds in this section yet.</p>`}
            </div>
          </section>
        `;
      }).join("");

      const orphan = labItems.filter(p => !usedIds.has(p.bucket || "personal"));
      if (orphan.length) {
        labEl.innerHTML += `
          <section class="lab-bucket reveal">
            <h3 class="lab-bucket-title">More builds</h3>
            <div class="lab-grid">${orphan.map(renderCard).join("")}</div>
          </section>
        `;
      }
    }

    const featuredNames = new Set(labItems.map(p => (p.name || "").toLowerCase()));
    // Also hide aliases that moved into buckets
    ["aurora health agent", "hr resume matching agent", "skills intelligence hr app"].forEach(n => featuredNames.add(n));
    const gitEl = document.getElementById("git-projects");
    if (gitEl) {
      const projects = (Array.isArray(a.gitProjects) ? a.gitProjects : [])
        .filter(p => !featuredNames.has((p.name || "").toLowerCase()));
      gitEl.innerHTML = projects.length
        ? projects.map(p => `
          <article class="git-project-card">
            <div class="git-project-media" style="${
              p.image
                ? `background-image:url('${escapeHtml(p.image)}')`
                : `background:linear-gradient(155deg, var(--accent), var(--accent-deep))`
            }" role="img" aria-label="${escapeHtml(p.name || "Project")}"></div>
            <div class="git-project-body">
              <h3>${escapeHtml(p.name || "Project")}</h3>
              <p>${escapeHtml(p.summary || "")}</p>
              <div class="btn-row">
                ${p.repoUrl
                  ? `<a class="btn btn-ghost btn-small git-project-link" href="${escapeHtml(p.repoUrl)}" target="_blank" rel="noopener">View repo →</a>`
                  : ""}
              </div>
            </div>
          </article>
        `).join("")
        : `<p style="color:var(--ink-soft);">Additional Git projects appear here.</p>`;
    }
  } catch (err) {
    console.error(err);
  }
});
