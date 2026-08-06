document.addEventListener("DOMContentLoaded", async () => {
  try {
    const content = await loadContent();
    await bootChrome(content);
    const a = content.aiJourney;
    applyPageHero(a);

    const story = document.getElementById("ai-story");
    if (story) {
      story.classList.add("rich-text");
      story.innerHTML = richHtml(a.story || "");
    }

    const username = a.githubUsername || "";
    const githubLink = document.getElementById("github-link");
    if (githubLink) githubLink.href = `https://github.com/${username}`;

    const railwayEl = document.getElementById("railway-projects");
    if (railwayEl) {
      railwayEl.innerHTML = (a.projects || []).map(p => `
        <div class="repo-card">
          <span class="badge-live">● project</span>
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

    const statusEl = document.getElementById("github-status");
    const reposEl = document.getElementById("github-repos");
    if (!username) {
      if (statusEl) statusEl.textContent = "Add your GitHub username in the editor to pull live repos.";
      return;
    }

    fetch(`https://api.github.com/users/${username}/repos?sort=updated&per_page=6`)
      .then(res => {
        if (!res.ok) throw new Error("GitHub API request failed");
        return res.json();
      })
      .then(repos => {
        if (!Array.isArray(repos) || repos.length === 0) {
          if (statusEl) statusEl.textContent = "No public repos found yet.";
          return;
        }
        if (statusEl) statusEl.textContent = "Most recently updated:";
        if (reposEl) {
          reposEl.innerHTML = repos.map(r => `
            <div class="repo-card">
              <h4>${escapeHtml(r.name)}</h4>
              <p>${escapeHtml(r.description || "No description yet.")}</p>
              <div class="repo-meta">
                <span>★ ${r.stargazers_count}</span>
                <span>${escapeHtml(r.language || "—")}</span>
              </div>
              <div class="btn-row" style="margin-top:14px;">
                <a class="btn btn-ghost" style="padding:8px 16px; font-size:0.85rem;" href="${escapeHtml(r.html_url)}" target="_blank" rel="noopener">View repo →</a>
              </div>
            </div>
          `).join("");
        }
      })
      .catch(() => {
        if (statusEl) statusEl.textContent = "Couldn't load live GitHub data right now — view the profile directly.";
      });
  } catch (err) {
    console.error(err);
  }
});
