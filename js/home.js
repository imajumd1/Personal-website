document.addEventListener("DOMContentLoaded", async () => {
  try {
    const content = await loadContent();
    await bootChrome(content);
    const h = content.home;

    const eyebrow = document.querySelector(".hero .eyebrow");
    const headline = document.querySelector(".hero h1");
    const pitch = document.querySelector(".hero .pitch");
    if (eyebrow) eyebrow.textContent = h.eyebrow || "";
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
        hero.innerHTML = "";
      } else {
        hero.innerHTML = `<span>${escapeHtml(h.heroLabel || "")}</span>`;
      }
    }

    renderPillars(h.highlights || []);
  } catch (err) {
    console.error(err);
  }
});

function renderPillars(items) {
  const section = document.querySelector(".highlights");
  if (!section || !items.length) return;

  const wrap = section.querySelector(".wrap") || section.appendChild(Object.assign(document.createElement("div"), { className: "wrap" }));
  wrap.innerHTML = `
    <div class="pillars-intro reveal in">
      <span class="eyebrow">Pillars</span>
      <h2>What defines the work</h2>
      <p>Scan the throughlines, then open one to read.</p>
    </div>
    <div class="pillar-stage reveal in" id="pillar-stage" aria-live="polite"></div>
    <div class="pillars-rail reveal in" role="tablist" aria-label="Pillars" id="pillars-rail"></div>
  `;

  const stage = wrap.querySelector("#pillar-stage");
  const rail = wrap.querySelector("#pillars-rail");

  rail.innerHTML = items.map((item, idx) => {
    const cut = truncateRich(item.text, 12);
    const title = escapeHtml(item.title || "Pillar");
    const cover = pillarCover(item);
    return `
      <button
        type="button"
        class="pillar-tab"
        role="tab"
        id="pillar-tab-${idx}"
        aria-selected="false"
        aria-controls="pillar-stage"
        data-pillar-index="${idx}"
      >
        <span class="pillar-tab-media" ${cover ? `style="background-image:url('${escapeHtml(cover)}')"` : ""}></span>
        <span class="pillar-tab-body">
          <span class="num">${escapeHtml(item.num || "")}</span>
          <span class="pillar-tab-title">${title}</span>
          <span class="pillar-tab-preview">${escapeHtml(htmlToPlainText(cut.previewHtml))}</span>
        </span>
        <span class="pillar-tab-arrow" aria-hidden="true">→</span>
      </button>
    `;
  }).join("");

  let active = 0;
  let primed = false;

  const select = (idx, { focusTab = false } = {}) => {
    active = (idx + items.length) % items.length;
    rail.querySelectorAll(".pillar-tab").forEach((tab, i) => {
      const on = i === active;
      tab.classList.toggle("is-active", on);
      tab.setAttribute("aria-selected", on ? "true" : "false");
      tab.tabIndex = on ? 0 : -1;
    });
    paintStage(stage, items[active], active, items.length);
    initStageSlideshow(stage);
    if (primed) {
      stage.classList.remove("is-swapping");
      void stage.offsetWidth;
      stage.classList.add("is-swapping");
    }
    primed = true;
    if (focusTab) {
      const tab = rail.querySelector(`.pillar-tab[data-pillar-index="${active}"]`);
      if (tab) tab.focus();
    }
  };

  rail.querySelectorAll(".pillar-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      select(parseInt(tab.dataset.pillarIndex, 10) || 0);
    });
  });

  rail.addEventListener("keydown", e => {
    const tabs = [...rail.querySelectorAll(".pillar-tab")];
    if (!tabs.length) return;
    let next = active;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") next = active + 1;
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") next = active - 1;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = items.length - 1;
    else return;
    e.preventDefault();
    select(next, { focusTab: true });
  });

  stage.addEventListener("click", e => {
    const btn = e.target.closest("[data-pillar-step]");
    if (!btn) return;
    const step = parseInt(btn.dataset.pillarStep, 10) || 0;
    select(active + step);
  });

  select(0);
}

function pillarSlides(item) {
  const slides = Array.isArray(item.slides) ? item.slides.filter(Boolean) : [];
  if (slides.length) return slides;
  return item.image ? [item.image] : [];
}

function pillarCover(item) {
  const slides = pillarSlides(item);
  return slides[0] || "";
}

function paintStage(stage, item, index, total) {
  const slides = pillarSlides(item);
  const title = escapeHtml(item.title || "Pillar");
  const media = slides.length
    ? `
      <div class="pillar-stage-media" data-pillar-slides>
        ${slides.map((src, s) => `
          <div class="slide${s === 0 ? " active" : ""}" style="background-image:url('${escapeHtml(src)}')"></div>
        `).join("")}
        ${slides.length > 1 ? `
          <div class="highlight-dots">
            ${slides.map((_, s) => `<button type="button" aria-label="Slide ${s + 1}" class="${s === 0 ? "active" : ""}" data-slide="${s}"></button>`).join("")}
          </div>
        ` : ""}
      </div>`
    : `
      <div class="pillar-stage-media is-fallback">
        <div class="slide-fallback">${title}</div>
      </div>`;

  stage.innerHTML = `
    ${media}
    <div class="pillar-stage-copy">
      <div class="pillar-stage-meta">
        <span class="num">${escapeHtml(item.num || "")}</span>
        <span class="pillar-stage-count">${index + 1} / ${total}</span>
      </div>
      <h3>${title}</h3>
      <div class="pillar-stage-text rich-text">${richHtml(item.text || "")}</div>
      <div class="pillar-stage-nav">
        <button type="button" class="pillar-nav-btn" data-pillar-step="-1" aria-label="Previous pillar">
          <span aria-hidden="true">←</span>
        </button>
        <button type="button" class="pillar-nav-btn" data-pillar-step="1" aria-label="Next pillar">
          <span aria-hidden="true">→</span>
        </button>
      </div>
    </div>
  `;
}

function initStageSlideshow(stage) {
  const media = stage.querySelector("[data-pillar-slides]");
  if (!media) return;
  const slides = [...media.querySelectorAll(".slide")];
  const dots = [...media.querySelectorAll(".highlight-dots button")];
  if (slides.length < 2) return;

  let i = 0;
  const show = next => {
    i = (next + slides.length) % slides.length;
    slides.forEach((s, n) => s.classList.toggle("active", n === i));
    dots.forEach((d, n) => d.classList.toggle("active", n === i));
  };

  dots.forEach(dot => {
    dot.addEventListener("click", e => {
      e.preventDefault();
      e.stopPropagation();
      show(parseInt(dot.dataset.slide, 10) || 0);
    });
  });

  let timer = setInterval(() => show(i + 1), 4200);
  media.addEventListener("mouseenter", () => clearInterval(timer));
  media.addEventListener("mouseleave", () => {
    clearInterval(timer);
    timer = setInterval(() => show(i + 1), 4200);
  });
}
