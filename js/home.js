document.addEventListener("DOMContentLoaded", async () => {
  try {
    const content = await loadContent();
    await bootChrome(content);
    const h = content.home || {};
    const site = content.site || {};

    const eyebrow = document.querySelector(".hero .eyebrow");
    const nameEl = document.querySelector(".hero-name");
    const headline = document.querySelector(".hero h1");
    const pitch = document.querySelector(".hero .pitch");
    if (eyebrow) eyebrow.textContent = h.eyebrow || "Builder-Executive";
    if (nameEl) nameEl.textContent = h.name || site.brand || "Ishita Majumdar";
    if (headline) headline.textContent = h.headline || "";
    if (pitch) {
      pitch.classList.add("rich-text");
      pitch.innerHTML = richHtml(h.pitch || "");
    }

    const hero = document.querySelector(".hero-image");
    if (hero) {
      if (h.heroImage) {
        hero.style.backgroundImage = `url('${h.heroImage}')`;
        hero.style.backgroundSize = "cover";
        hero.style.backgroundPosition = "center";
        hero.setAttribute("aria-label", h.heroLabel || "Portrait of Ishita Majumdar");
      }
    }

    const primary = document.querySelector('.hero .btn-primary');
    const secondary = document.querySelector('.hero .btn-ghost');
    if (primary && h.ctaPrimary) {
      primary.textContent = h.ctaPrimary.label || primary.textContent;
      primary.href = h.ctaPrimary.href || primary.href;
    }
    if (secondary && h.ctaSecondary) {
      secondary.textContent = h.ctaSecondary.label || secondary.textContent;
      secondary.href = h.ctaSecondary.href || secondary.href;
    }

    renderProof(h.proofMetrics || []);
    renderWhatIDo(h.whatIDo || []);
    renderImpact((h.selectedImpact || []).slice(0, 6));
    renderCareerArc(h.careerArc || []);
    renderBeliefs(h.beliefs || []);
    renderLab((content.aiLab?.items || []).slice(0, 6));
    renderPerspectives(h.featuredPerspectives || []);
    renderSpeaking((content.speaking?.items || []).slice(0, 3));
  } catch (err) {
    console.error(err);
  }
});

function renderProof(items) {
  const el = document.getElementById("proof-metrics");
  if (!el) return;
  el.innerHTML = items.map(m => `
    <div class="proof-item reveal in">
      <span class="proof-value">${escapeHtml(m.value || "")}</span>
      <span class="proof-label">${escapeHtml(m.label || "")}</span>
    </div>
  `).join("");
}

function renderWhatIDo(items) {
  const el = document.getElementById("what-i-do-grid");
  if (!el) return;
  // Always keep the leverage section as a 3-column row (stacks on mobile via CSS).
  el.classList.remove("pillars-5");
  el.innerHTML = items.map((p, i) => `
    <article class="pillar-card reveal in">
      <span class="num">${String(i + 1).padStart(2, "0")}</span>
      <h3>${escapeHtml(p.title || "")}</h3>
      <p>${escapeHtml(p.text || "")}</p>
    </article>
  `).join("");
}

function renderImpact(items) {
  const el = document.getElementById("impact-grid");
  if (!el) return;
  el.innerHTML = items.map(item => `
    <article class="impact-card reveal in">
      <span class="tag">${escapeHtml(item.org || "")}</span>
      <h3>${escapeHtml(item.title || "")}</h3>
      <dl class="impact-dl">
        <div><dt>Challenge</dt><dd>${escapeHtml(item.challenge || "")}</dd></div>
        <div><dt>Built</dt><dd>${escapeHtml(item.action || "")}</dd></div>
        <div><dt>Impact</dt><dd>${escapeHtml(item.impact || "")}</dd></div>
      </dl>
    </article>
  `).join("");
}

function renderCareerArc(items) {
  const el = document.getElementById("career-arc-list");
  if (!el) return;
  el.innerHTML = items.map(s => `
    <li class="career-arc-item reveal in">
      <span class="career-stage">${escapeHtml(s.stage || "")}</span>
      <span class="career-detail">${escapeHtml(s.detail || "")}</span>
    </li>
  `).join("");
}

function renderBeliefs(items) {
  const el = document.getElementById("beliefs-grid");
  if (!el) return;
  el.innerHTML = items.map(b => `
    <article class="belief-card reveal in">
      <h3>${escapeHtml(b.title || "")}</h3>
      <p>${escapeHtml(b.text || "")}</p>
      ${b.link ? `<a class="go" href="${escapeHtml(b.link)}">${escapeHtml(b.linkLabel || "Read more")} →</a>` : ""}
    </article>
  `).join("");
}

function renderLab(items) {
  const el = document.getElementById("lab-grid");
  if (!el) return;
  el.innerHTML = items.map(p => {
    const media = p.image
      ? `style="background-image:url('${escapeHtml(p.image)}')"`
      : `style="background:linear-gradient(155deg, var(--accent), var(--accent-deep))"`;
    const links = [
      p.liveUrl ? `<a class="btn btn-primary btn-small" href="${escapeHtml(p.liveUrl)}" target="_blank" rel="noopener">Live demo</a>` : "",
      p.repoUrl ? `<a class="btn btn-ghost btn-small" href="${escapeHtml(p.repoUrl)}" target="_blank" rel="noopener">GitHub</a>` : ""
    ].filter(Boolean).join("");
    return `
      <article class="lab-card reveal in">
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
  }).join("") || `<p style="color:var(--ink-soft);">Builds coming soon.</p>`;
}

function renderPerspectives(items) {
  const el = document.getElementById("perspective-grid");
  if (!el) return;
  el.innerHTML = items.map(m => `
    <a class="perspective-card reveal in" href="${escapeHtml(m.href || "musings.html")}">
      <span class="tag">${escapeHtml(m.category || "")}</span>
      <h3>${escapeHtml(m.title || "")}</h3>
      <p>${escapeHtml(m.thesis || "")}</p>
      <div class="perspective-meta">
        <span>${escapeHtml(m.readingTime || "")}</span>
        ${m.date ? `<span>${escapeHtml(m.date)}</span>` : ""}
      </div>
    </a>
  `).join("");
}

function renderSpeaking(items) {
  const el = document.getElementById("speaking-list");
  if (!el) return;
  el.innerHTML = items.map(s => `
    <article class="speaking-card reveal in">
      <h3>${escapeHtml(s.title || "")}</h3>
      <div class="meta">${escapeHtml([s.event, s.meta].filter(Boolean).join(" · "))}</div>
      <p>${escapeHtml(s.blurb || "")}</p>
    </article>
  `).join("") || `<p style="color:var(--ink-soft);">Speaking calendar expanding — check back soon.</p>`;
}
