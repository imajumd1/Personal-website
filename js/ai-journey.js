document.addEventListener("DOMContentLoaded", async () => {
  try {
    const content = await loadContent();
    await bootChrome(content);
    const a = content.aiJourney || {};
    applyPageHero(a);

    const story = document.getElementById("ai-story");
    if (story) {
      story.classList.add("rich-text");
      story.innerHTML = richHtml(a.story || "");
    }

    const username = a.githubUsername || "imajumd1";
    const githubLink = document.getElementById("github-link");
    if (githubLink) githubLink.href = `https://github.com/${username}`;

    const gitEl = document.getElementById("git-projects");
    if (gitEl) {
      const projects = Array.isArray(a.gitProjects) ? a.gitProjects : [];
      gitEl.innerHTML = projects.length
        ? projects.map(p => `
          <article class="git-project-card">
            <div class="git-project-media" style="${
              p.image
                ? `background-image:url('${escapeHtml(p.image)}')`
                : `background:linear-gradient(155deg, var(--accent), var(--accent-deep))`
            }"></div>
            <div class="git-project-body">
              <h3>${escapeHtml(p.name || "Project")}</h3>
              <p>${escapeHtml(p.summary || "")}</p>
              ${p.repoUrl
                ? `<a class="btn btn-ghost git-project-link" href="${escapeHtml(p.repoUrl)}" target="_blank" rel="noopener">View repo →</a>`
                : ""}
            </div>
          </article>
        `).join("")
        : `<p style="color:var(--ink-soft);">No Git projects yet — add them in the admin editor.</p>`;
    }

    const railwayEl = document.getElementById("railway-projects");
    if (railwayEl) {
      railwayEl.innerHTML = (a.projects || []).map(p => `
        <div class="repo-card">
          <span class="badge-live">● featured</span>
          <h4>${escapeHtml(p.name)}</h4>
          <div class="rich-text">${richHtml(p.description)}</div>
          <div class="repo-meta">
            ${(p.tags || []).map(t => `<span>#${escapeHtml(t)}</span>`).join("")}
          </div>
          <div class="btn-row" style="margin-top:14px;">
            ${p.liveUrl
              ? `<a class="btn btn-primary" style="padding:8px 16px; font-size:0.85rem;" href="${escapeHtml(p.liveUrl)}" target="_blank" rel="noopener">Open live →</a>`
              : ""}
            ${p.repoUrl
              ? `<a class="btn btn-ghost" style="padding:8px 16px; font-size:0.85rem;" href="${escapeHtml(p.repoUrl)}" target="_blank" rel="noopener">Code</a>`
              : ""}
          </div>
        </div>
      `).join("");
    }
  } catch (err) {
    console.error(err);
  }
});
