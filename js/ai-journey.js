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

    const buildsEl = document.getElementById("featured-builds");
    if (buildsEl) {
      const rawBuilds = Array.isArray(a.featuredBuilds)
        ? a.featuredBuilds
        : Array.isArray(a.projects)
          ? a.projects.map(legacyProjectToBuild)
          : [];
      // Featured Builds promise a public URL — skip cards without a live link.
      const builds = rawBuilds.filter(p => p && String(p.liveUrl || "").trim());
      buildsEl.innerHTML = builds.length
        ? builds.map(p => {
            const img = String(p.image || "").trim();
            const mediaStyle = img
              ? `background-image:url('${escapeHtml(img)}');background-size:cover;background-position:center`
              : `background:linear-gradient(155deg, var(--accent), var(--accent-deep))`;
            return `
          <article class="git-project-card">
            <div class="git-project-media" style="${mediaStyle}"></div>
            <div class="git-project-body">
              <h3>${escapeHtml(p.name || "Build")}</h3>
              <p>${escapeHtml(p.summary || "")}</p>
              <a class="btn btn-primary git-project-link" href="${escapeHtml(String(p.liveUrl).trim())}" target="_blank" rel="noopener">Open live →</a>
            </div>
          </article>`;
          }).join("")
        : `<p style="color:var(--ink-soft);">No featured builds with a public Railway URL yet — add live URLs in the admin editor.</p>`;
    }
  } catch (err) {
    console.error(err);
  }
});

function legacyProjectToBuild(p) {
  const raw = p.summary || p.description || "";
  const summary = String(raw).replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  return {
    name: p.name || "",
    summary,
    image: p.image || "",
    liveUrl: p.liveUrl || ""
  };
}
