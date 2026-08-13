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

    const primary = document.querySelector(".hero .btn-primary");
    const secondary = document.querySelector(".hero .btn-ghost");
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

function impactTeaser(item) {
  const raw = item.teaser || item.challenge || item.impact || "";
  return truncateWords(raw, 18);
}

function renderImpact(items) {
  const el = document.getElementById("impact-grid");
  if (!el) return;
  el.innerHTML = items.map((item, i) => {
    const teaser = impactTeaser(item);
    const id = `impact-detail-${i}`;
    const mediaStyle = item.image
      ? ` style="background-image:url('${escapeHtml(item.image)}')"`
      : "";
    const mediaAttrs = item.image
      ? ` role="img" aria-label="${escapeHtml(item.title || item.org || "Case study")}"`
      : ` aria-hidden="true"`;
    return `
    <article class="impact-card impact-card-compact reveal in">
      <div class="impact-media"${mediaStyle}${mediaAttrs}></div>
      <div class="impact-body">
        <span class="tag">${escapeHtml(item.org || "")}</span>
        <h3>${escapeHtml(item.title || "")}</h3>
        <p class="impact-teaser">${escapeHtml(teaser.preview)}</p>
        <button type="button" class="btn btn-ghost btn-small impact-read-more" aria-expanded="false" aria-controls="${id}">
          Read More
        </button>
        <div class="impact-detail" id="${id}" hidden>
          <dl class="impact-dl">
            <div><dt>Challenge</dt><dd>${escapeHtml(item.challenge || "")}</dd></div>
            <div><dt>Built</dt><dd>${escapeHtml(item.action || "")}</dd></div>
            <div><dt>Impact</dt><dd>${escapeHtml(item.impact || "")}</dd></div>
          </dl>
        </div>
      </div>
    </article>
  `;
  }).join("");

  el.querySelectorAll(".impact-read-more").forEach(btn => {
    btn.addEventListener("click", () => {
      const detail = document.getElementById(btn.getAttribute("aria-controls"));
      if (!detail) return;
      const open = detail.hasAttribute("hidden");
      if (open) {
        detail.removeAttribute("hidden");
        btn.setAttribute("aria-expanded", "true");
        btn.textContent = "Show less";
        btn.closest(".impact-card")?.classList.add("is-expanded");
      } else {
        detail.setAttribute("hidden", "");
        btn.setAttribute("aria-expanded", "false");
        btn.textContent = "Read More";
        btn.closest(".impact-card")?.classList.remove("is-expanded");
      }
    });
  });
}
