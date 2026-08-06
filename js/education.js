document.addEventListener("DOMContentLoaded", async () => {
  try {
    const content = await loadContent();
    await bootChrome(content);
    const e = content.education;
    applyPageHero(e);

    const timeline = document.getElementById("edu-timeline");
    if (timeline) {
      timeline.innerHTML = (e.schools || []).map(item => `
        <div class="timeline-item">
          <h3>${escapeHtml(item.title)}</h3>
          <div class="meta">${escapeHtml(item.meta)}</div>
          <div class="rich-text">${richHtml(item.blurb)}</div>
          <button class="learned-toggle" onclick="toggleLearn(this)">What I learned →</button>
          <div class="learned-box">
            <div class="rich-text" style="padding:14px 16px;">${richHtml(item.learned)}</div>
          </div>
        </div>
      `).join("");
    }
  } catch (err) {
    console.error(err);
  }
});

function toggleLearn(btn) {
  const box = btn.nextElementSibling;
  box.classList.toggle("open");
  btn.textContent = box.classList.contains("open") ? "What I learned ↑" : "What I learned →";
}
