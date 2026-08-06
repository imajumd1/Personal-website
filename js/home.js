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

    const section = document.querySelector(".highlights");
    if (section && !section.querySelector(".pillars-intro")) {
      const wrap = section.querySelector(".wrap");
      const intro = document.createElement("div");
      intro.className = "pillars-intro reveal in";
      intro.innerHTML = `
        <span class="eyebrow">Pillars</span>
        <h2>What defines the work</h2>
        <p>A quick scan of the throughlines — expand any card for the full story.</p>
      `;
      wrap.insertBefore(intro, wrap.firstChild);
    }

    const grid = document.querySelector(".highlights-grid");
    if (grid && h.highlights) {
      grid.innerHTML = h.highlights.map((item, idx) => {
        const slides = pillarSlides(item);
        const cut = truncateRich(item.text, 24);
        const media = slides.length
          ? `
            <div class="highlight-media" data-pillar="${idx}">
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
            <div class="highlight-media">
              <div class="slide-fallback">${escapeHtml(item.title || "Pillar")}</div>
            </div>`;

        return `
          <article class="highlight-card reveal in" data-pillar-card="${idx}">
            ${media}
            <div class="highlight-body">
              <span class="num">${escapeHtml(item.num)}</span>
              <h3>${escapeHtml(item.title)}</h3>
              <div class="pillar-text rich-text${cut.truncated ? "" : " is-short"}">${cut.previewHtml}</div>
              ${cut.truncated ? `<button type="button" class="more-btn" aria-expanded="false" data-full="${encodeURIComponent(cut.fullHtml)}" data-preview="${encodeURIComponent(cut.previewHtml)}">More</button>` : `<span class="more-btn more-btn-spacer" aria-hidden="true"></span>`}
            </div>
          </article>
        `;
      }).join("");

      initPillarSlideshows(grid);
      initPillarMore(grid);
    }
  } catch (err) {
    console.error(err);
  }
});

function pillarSlides(item) {
  const slides = Array.isArray(item.slides) ? item.slides.filter(Boolean) : [];
  if (slides.length) return slides;
  return item.image ? [item.image] : [];
}

function initPillarSlideshows(root) {
  root.querySelectorAll(".highlight-media[data-pillar]").forEach(media => {
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
        show(parseInt(dot.dataset.slide, 10) || 0);
      });
    });

    let timer = setInterval(() => show(i + 1), 4200);
    media.addEventListener("mouseenter", () => clearInterval(timer));
    media.addEventListener("mouseleave", () => {
      clearInterval(timer);
      timer = setInterval(() => show(i + 1), 4200);
    });
  });
}

function initPillarMore(root) {
  root.querySelectorAll(".more-btn:not(.more-btn-spacer)").forEach(btn => {
    btn.addEventListener("click", () => {
      const card = btn.closest(".highlight-card");
      const text = card.querySelector(".pillar-text");
      const expanded = btn.getAttribute("aria-expanded") === "true";
      if (expanded) {
        text.innerHTML = decodeURIComponent(btn.dataset.preview || "");
        text.classList.remove("is-expanded");
        btn.textContent = "More";
        btn.setAttribute("aria-expanded", "false");
        card.classList.remove("expanded");
      } else {
        text.innerHTML = decodeURIComponent(btn.dataset.full || "");
        text.classList.add("is-expanded");
        btn.textContent = "Less";
        btn.setAttribute("aria-expanded", "true");
        card.classList.add("expanded");
      }
    });
  });
}
