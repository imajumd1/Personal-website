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
          learned: ""
        }));

    const labEl = document.getElementById("lab-grid");
    if (labEl) {
      labEl.innerHTML = labItems.map(p => {
        const media = p.image
          ? `style="background-image:url('${escapeHtml(p.image)}')"`
          : `style="background:linear-gradient(155deg, var(--accent), var(--accent-deep))"`;
        const links = [
          p.repoUrl ? `<a class="btn btn-ghost btn-small" href="${escapeHtml(p.repoUrl)}" target="_blank" rel="noopener">GitHub</a>` : ""
        ].filter(Boolean).join("");
        return `
          <article class="lab-card">
            <div class="lab-media" ${media} role="img" aria-label="${escapeHtml(p.name || "Project")}"></div>
            <div class="lab-body">
              <h3>${escapeHtml(p.name || "")}</h3>
              <p class="lab-summary">${escapeHtml(p.summary || "")}</p>
              ${p.why ? `<p><strong>Why</strong> — ${escapeHtml(p.why)}</p>` : ""}
              ${p.tech ? `<p class="lab-meta"><strong>Tech</strong> — ${escapeHtml(p.tech)}</p>` : ""}
              ${p.learned ? `<p><strong>Learned</strong> — ${escapeHtml(p.learned)}</p>` : ""}
              <div class="btn-row">${links}</div>
            </div>
          </article>
        `;
      }).join("") || `<p style="color:var(--ink-soft);">No lab builds yet.</p>`;
    }

    const featuredNames = new Set(labItems.map(p => (p.name || "").toLowerCase()));
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
              ${p.repoUrl
                ? `<a class="btn btn-ghost git-project-link" href="${escapeHtml(p.repoUrl)}" target="_blank" rel="noopener">View repo →</a>`
                : ""}
            </div>
          </article>
        `).join("")
        : `<p style="color:var(--ink-soft);">Additional Git projects appear here.</p>`;
    }
  } catch (err) {
    console.error(err);
  }
});
