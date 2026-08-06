let ARTWORKS = [];

function openLightbox(i) {
  const a = ARTWORKS[i];
  const lb = document.getElementById("lightbox");
  const img = document.getElementById("lightbox-img");
  img.style.cssText = a.image
    ? `background-image:url('${a.image}'); background-size:cover; background-position:center;`
    : `background:linear-gradient(150deg, ${(a.colors || ["#1f5f52", "#b5651d"])[0]}, ${(a.colors || ["#1f5f52", "#b5651d"])[1]});`;
  document.getElementById("lightbox-title").textContent = a.title;
  const sum = document.getElementById("lightbox-summary");
  sum.classList.add("rich-text");
  sum.innerHTML = richHtml(a.summary);
  lb.classList.add("open");
}

document.addEventListener("DOMContentLoaded", async () => {
  try {
    const content = await loadContent();
    await bootChrome(content);
    const page = content.art || {};
    applyPageHero(page);
    ARTWORKS = pageItems(page);

    const grid = document.getElementById("art-masonry");
    if (grid) {
      grid.innerHTML = ARTWORKS.map((a, i) => `
        <div class="art-tile" onclick="openLightbox(${i})">
          <div class="art-img" style="--ar:${a.aspect || 1}; ${
            a.image
              ? `background-image:url('${escapeHtml(a.image)}'); background-size:cover; background-position:center;`
              : `--c1:${(a.colors || ["#1f5f52", "#b5651d"])[0]}; --c2:${(a.colors || ["#1f5f52", "#b5651d"])[1]};`
          }"></div>
          <div class="art-caption">
            <h4>${escapeHtml(a.title)}</h4>
            <p>${escapeHtml((() => { const plain = htmlToPlainText(a.summary||""); return plain.length > 70 ? plain.slice(0,70)+"…" : plain; })())}</p>
          </div>
        </div>
      `).join("");
    }

    document.getElementById("lightbox-close")?.addEventListener("click", () => {
      document.getElementById("lightbox").classList.remove("open");
    });
    document.getElementById("lightbox")?.addEventListener("click", e => {
      if (e.target.id === "lightbox") e.target.classList.remove("open");
    });
  } catch (err) {
    console.error(err);
  }
});
