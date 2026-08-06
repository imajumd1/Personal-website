document.addEventListener("DOMContentLoaded", async () => {
  try {
    const content = await loadContent();
    await bootChrome(content);
    const h = content.hiking || {};
    applyPageHero(h);

    const HIKE_STATS = h.stats || [];
    const TRIPS = h.trips || [];

    const statRow = document.getElementById("stat-row");
    if (statRow) {
      statRow.innerHTML = HIKE_STATS.map((s, i) => `
        <div class="stat-box">
          <span class="stat-num" data-target="${s.num}" id="stat-${i}">0</span>
          <span class="stat-label">${escapeHtml(s.label)}</span>
        </div>
      `).join("");

      document.querySelectorAll(".stat-num").forEach(el => {
        const target = parseInt(el.dataset.target, 10) || 0;
        if (target === 0) { el.textContent = "—"; return; }
        let current = 0;
        const step = Math.max(1, Math.ceil(target / 40));
        const timer = setInterval(() => {
          current += step;
          if (current >= target) { current = target; clearInterval(timer); }
          el.textContent = current.toLocaleString();
        }, 30);
      });
    }

    const trailList = document.getElementById("trail-list");
    if (trailList) {
      trailList.innerHTML = TRIPS.map(t => {
        const photoStyle = t.photo
          ? `background-image:url('${escapeHtml(t.photo)}'); background-size:cover; background-position:center;`
          : `background:linear-gradient(160deg, ${(t.colors || ["#274b3e", "#6f8f45"])[0]}, ${(t.colors || ["#274b3e", "#6f8f45"])[1]});`;
        return `
          <div class="trail-card reveal in">
            <div class="trail-photo" style="${photoStyle}"></div>
            <div class="trail-info">
              <h3>${escapeHtml(t.name)}</h3>
              <div class="meta">${escapeHtml(t.meta)}</div>
              <div class="rich-text">${richHtml(t.story)}</div>
            </div>
          </div>
        `;
      }).join("");
    }
  } catch (err) {
    console.error(err);
  }
});
