document.addEventListener("DOMContentLoaded", async () => {
  try {
    const content = await loadContent();
    await bootChrome(content);
    const page = content.books || {};
    applyPageHero(page);
    const BOOKS = pageItems(page);
    const grid = document.getElementById("books-grid");
    if (!grid) return;
    grid.innerHTML = BOOKS.map((b, i) => `
      <div class="book-card" id="book-${i}">
        <div class="book-card-inner" onclick="document.getElementById('book-${i}').classList.toggle('flipped')">
          <div class="book-face book-front">
            <div class="book-cover-art" style="${
              b.cover
                ? `background-image:url('${escapeHtml(b.cover)}'); background-size:cover; background-position:center;`
                : `background:linear-gradient(160deg, ${(b.colors || ["#1f5f52", "#0a1f1a"])[0]}, ${(b.colors || ["#1f5f52", "#0a1f1a"])[1]});`
            }"></div>
            <span class="flip-hint">flip →</span>
            <h4>${escapeHtml(b.title)}</h4>
            <div class="author">${escapeHtml(b.author)}</div>
          </div>
          <div class="book-face book-back">
            <h4>${escapeHtml(b.title)}</h4>
            <div class="rating">${"★".repeat(b.rating || 0)}${"☆".repeat(5 - (b.rating || 0))}</div>
            <div class="rich-text">${richHtml(b.summary)}</div>
          </div>
        </div>
      </div>
    `).join("");
  } catch (err) {
    console.error(err);
  }
});
