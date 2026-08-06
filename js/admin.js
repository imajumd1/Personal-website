let content = null;
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

function setStatus(msg, kind = "") {
  const el = $("#status");
  el.textContent = msg;
  el.className = "status-pill" + (kind ? ` ${kind}` : "");
}

function escapeHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function paragraphsToHtml(arrOrHtml) {
  if (Array.isArray(arrOrHtml)) {
    return arrOrHtml.map(p => `<p>${rteEscape(p)}</p>`).join("");
  }
  return plainToHtml(arrOrHtml || "");
}

/** Ensure books/musings/art are { eyebrow, title, lede, items } objects. */
function normalizeListPage(section, defaults = {}) {
  if (Array.isArray(section)) {
    return {
      eyebrow: defaults.eyebrow || "",
      title: defaults.title || "",
      lede: defaults.lede || "",
      items: section
    };
  }
  return {
    eyebrow: section?.eyebrow || defaults.eyebrow || "",
    title: section?.title || defaults.title || "",
    lede: section?.lede || defaults.lede || "",
    items: Array.isArray(section?.items) ? section.items : []
  };
}

function normalizeContent(raw) {
  const c = raw || {};
  c.books = normalizeListPage(c.books, {
    eyebrow: "04 / Books",
    title: "What I'm Reading",
    lede: "<p>Click a cover to flip it over for the summary.</p>"
  });
  c.musings = normalizeListPage(c.musings, {
    eyebrow: "05 / Musings",
    title: "My $0.02",
    lede: "<p>No timestamps on purpose — an idea here should read the same whether you find it today or in five years.</p>"
  });
  c.art = normalizeListPage(c.art, {
    eyebrow: "06 / Art",
    title: "My Art",
    lede: "<p>A portfolio in progress. Click any piece for the full story behind it.</p>"
  });
  c.biography = c.biography || {};
  c.education = c.education || {};
  c.aiJourney = c.aiJourney || {};
  c.hiking = c.hiking || {};
  if (!c.biography.title) c.biography.title = "Who I Am";
  if (!c.biography.eyebrow) c.biography.eyebrow = "01 / Biography";
  if (!c.education.title) c.education.title = "How I Learned";
  if (!c.education.eyebrow) c.education.eyebrow = "02 / Education";
  if (!c.aiJourney.title) c.aiJourney.title = "Building With AI";
  if (!c.aiJourney.eyebrow) c.aiJourney.eyebrow = "03 / AI Journey";
  if (!Array.isArray(c.aiJourney.gitProjects)) c.aiJourney.gitProjects = [];
  if (!Array.isArray(c.aiJourney.projects)) c.aiJourney.projects = [];
  if (!c.hiking.title) c.hiking.title = "On the Trail";
  if (!c.hiking.eyebrow) c.hiking.eyebrow = "07 / Hiking";
  return c;
}

function mountRte(card, key, html, opts) {
  const mount = card.querySelector(`[data-rte-mount="${key}"]`);
  if (!mount) return;
  const rte = createRte(html, opts);
  rte.dataset.rteKey = key;
  mount.replaceWith(rte);
}

async function uploadFile(file, folder) {
  const fd = new FormData();
  fd.append("folder", folder);
  fd.append("file", file);
  const res = await fetch("/api/upload", { method: "POST", body: fd, credentials: "same-origin" });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 || data.error === "Unauthorized") {
    setStatus("Session expired — sign in again", "error");
    setTimeout(() => { location.href = "login.html?next=admin.html"; }, 700);
    throw new Error("Unauthorized");
  }
  if (!res.ok || !data.ok) throw new Error(data.error || "Upload failed");
  return data;
}

function bindNav() {
  $$("#admin-nav button").forEach(btn => {
    btn.addEventListener("click", () => {
      $$("#admin-nav button").forEach(b => b.classList.remove("active"));
      $$(".panel").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      $(`#panel-${btn.dataset.panel}`).classList.add("active");
    });
  });
}

function renderHome() {
  const h = content.home;
  $("#home-eyebrow").value = h.eyebrow || "";
  $("#home-headline").value = h.headline || "";
  setStaticRte("home-pitch", h.pitch || "", { minHeight: "120px" });
  $("#home-heroImage").value = h.heroImage || "";
  $("#home-heroLabel").value = h.heroLabel || "";
  updateHeroPreview();
  const list = $("#home-highlights");
  list.innerHTML = "";
  (h.highlights || []).forEach((item, i) => {
    list.appendChild(highlightCard(item, i));
  });
}

function updateHeroPreview() {
  const path = $("#home-heroImage").value.trim();
  const img = $("#home-hero-preview");
  const empty = $("#home-hero-empty");
  if (path) {
    img.src = path;
    img.hidden = false;
    empty.style.display = "none";
  } else {
    img.hidden = true;
    empty.style.display = "flex";
  }
}

function highlightCard(item, i) {
  const slides = Array.isArray(item.slides) && item.slides.length
    ? item.slides
    : (item.image ? [item.image] : []);
  const el = document.createElement("div");
  el.className = "item-card";
  el.dataset.index = i;
  el.innerHTML = `
    <div class="item-card-head">
      <strong>Pillar ${i + 1}</strong>
      <button type="button" class="btn btn-danger btn-small" data-remove="highlight">Remove</button>
    </div>
    <div class="row-2">
      <div class="field"><label>Number / label</label><input data-k="num" value="${escapeHtml(item.num)}"></div>
      <div class="field"><label>Title</label><input data-k="title" value="${escapeHtml(item.title)}"></div>
    </div>
    <div class="field"><label>Text</label><div data-rte-mount="text"></div></div>
    <div class="field">
      <label>Slides (JPEG / PNG / WebP)</label>
      <p class="hint">First image is the cover on the pillar. Add more for an auto-rotating slideshow.</p>
      <div class="slide-list" data-slides>
        ${slides.map((src, s) => `
          <div class="slide-item" data-src="${escapeHtml(src)}">
            <img class="thumb" src="${escapeHtml(src)}" alt="Slide ${s + 1}">
            <div class="upload-row">
              <span class="hint">Slide ${s + 1}${s === 0 ? " · cover" : ""}</span>
              <button type="button" class="btn btn-danger btn-small" data-remove-slide>Remove</button>
            </div>
          </div>
        `).join("") || `<p class="hint">No slides yet — upload one below.</p>`}
      </div>
      <div class="upload-row" style="margin-top:12px;">
        <input type="file" accept="image/jpeg,image/jpg,image/png,image/webp,image/gif" data-upload-folder="pillars" multiple>
        <button type="button" class="btn btn-ghost btn-small" data-add-pillar-slides>Upload slide(s)</button>
      </div>
    </div>
  `;
  mountRte(el, "text", item.text || "", { minHeight: "100px" });
  return el;
}

function renderBiography() {
  const b = content.biography;
  $("#bio-eyebrow").value = b.eyebrow || "";
  $("#bio-title").value = b.title || "";
  setStaticRte("bio-lede", b.lede || "");
  setStaticRte("bio-summary", paragraphsToHtml(b.summary), { minHeight: "160px" });
  const career = $("#bio-career");
  career.innerHTML = "";
  (b.career || []).forEach((item, i) => career.appendChild(careerCard(item, i)));
  const callouts = $("#bio-callouts");
  callouts.innerHTML = "";
  (b.callouts || []).forEach((item, i) => callouts.appendChild(calloutCard(item, i)));
}

function careerCard(item, i) {
  const files = Array.isArray(item.attachments) ? item.attachments : [];
  const el = document.createElement("div");
  el.className = "item-card";
  el.innerHTML = `
    <div class="item-card-head">
      <strong>Role ${i + 1}</strong>
      <button type="button" class="btn btn-danger btn-small" data-remove="career">Remove</button>
    </div>
    <div class="field"><label>Title</label><input data-k="title" value="${escapeHtml(item.title)}"></div>
    <div class="field"><label>Meta (dates / location)</label><input data-k="meta" value="${escapeHtml(item.meta)}"></div>
    <div class="field"><label>Description</label><div data-rte-mount="text"></div></div>
    <div class="field">
      <label>Documents & slides</label>
      <p class="hint">Upload PDFs, PowerPoint, Keynote, Word, images, or zips for this role.</p>
      <div class="attach-list">
        ${files.map((f, fi) => `
          <div class="attach-item" data-path="${escapeHtml(f.path)}" data-name="${escapeHtml(f.name || f.path)}" data-type="${escapeHtml(f.type || "")}">
            <span class="hint">${escapeHtml((f.type || "file").toUpperCase())} · ${escapeHtml(f.name || f.path)}</span>
            <button type="button" class="btn btn-danger btn-small" data-remove-attach>Remove</button>
          </div>
        `).join("") || `<p class="hint">No files yet.</p>`}
      </div>
      <div class="upload-row" style="margin-top:10px;">
        <input type="file" accept=".pdf,.ppt,.pptx,.key,.doc,.docx,.txt,.rtf,.xls,.xlsx,.csv,.zip,image/*" data-upload-folder="roles" multiple>
        <button type="button" class="btn btn-ghost btn-small" data-add-role-files>Upload file(s)</button>
      </div>
    </div>
  `;
  mountRte(el, "text", item.text || "", { minHeight: "120px" });
  return el;
}

function calloutCard(item, i) {
  const el = document.createElement("div");
  el.className = "item-card";
  el.innerHTML = `
    <div class="item-card-head">
      <strong>Callout ${i + 1}</strong>
      <button type="button" class="btn btn-danger btn-small" data-remove="callout">Remove</button>
    </div>
    <div class="field"><label>Title</label><input data-k="title" value="${escapeHtml(item.title)}"></div>
    <div class="field"><label>Text</label><div data-rte-mount="text"></div></div>
  `;
  mountRte(el, "text", item.text || "");
  return el;
}

function renderEducation() {
  $("#edu-eyebrow").value = content.education.eyebrow || "";
  $("#edu-title").value = content.education.title || "";
  setStaticRte("edu-lede", content.education.lede || "");
  const list = $("#edu-schools");
  list.innerHTML = "";
  (content.education.schools || []).forEach((item, i) => list.appendChild(schoolCard(item, i)));
}

function schoolCard(item, i) {
  const el = document.createElement("div");
  el.className = "item-card";
  el.innerHTML = `
    <div class="item-card-head">
      <strong>School ${i + 1}</strong>
      <button type="button" class="btn btn-danger btn-small" data-remove="school">Remove</button>
    </div>
    <div class="field"><label>School / program</label><input data-k="title" value="${escapeHtml(item.title)}"></div>
    <div class="field"><label>Meta</label><input data-k="meta" value="${escapeHtml(item.meta)}"></div>
    <div class="field"><label>Blurb</label><div data-rte-mount="blurb"></div></div>
    <div class="field"><label>What I learned</label><div data-rte-mount="learned"></div></div>
  `;
  mountRte(el, "blurb", item.blurb || "");
  mountRte(el, "learned", item.learned || "");
  return el;
}

function renderAI() {
  const a = content.aiJourney;
  $("#ai-eyebrow").value = a.eyebrow || "";
  $("#ai-title").value = a.title || "";
  setStaticRte("ai-lede", a.lede || "");
  setStaticRte("ai-story", paragraphsToHtml(a.story), { minHeight: "140px" });
  $("#ai-github").value = a.githubUsername || "";
  const gitList = $("#ai-git-projects");
  gitList.innerHTML = "";
  (a.gitProjects || []).forEach((item, i) => gitList.appendChild(gitProjectCard(item, i)));
  const list = $("#ai-projects");
  list.innerHTML = "";
  (a.projects || []).forEach((item, i) => list.appendChild(projectCard(item, i)));
}

function gitProjectCard(item, i) {
  const el = document.createElement("div");
  el.className = "item-card";
  el.innerHTML = `
    <div class="item-card-head">
      <strong>Git project ${i + 1}</strong>
      <button type="button" class="btn btn-danger btn-small" data-remove="gitProject">Remove</button>
    </div>
    <div class="field"><label>Name</label><input data-k="name" value="${escapeHtml(item.name || "")}"></div>
    <div class="field"><label>Summary</label><textarea data-k="summary" rows="3">${escapeHtml(item.summary || "")}</textarea></div>
    <div class="field"><label>Cover image path</label><input data-k="image" value="${escapeHtml(item.image || "")}"></div>
    <div class="upload-row">
      <input type="file" accept="image/*" data-upload-folder="projects">
      <button type="button" class="btn btn-ghost btn-small" data-upload-into="image">Upload cover</button>
    </div>
    ${item.image ? `<img class="thumb" src="${escapeHtml(item.image)}" alt="">` : `<div class="thumb empty">No cover yet</div>`}
    <div class="field"><label>GitHub repo URL</label><input data-k="repoUrl" value="${escapeHtml(item.repoUrl || "")}"></div>
  `;
  return el;
}

function projectCard(item, i) {
  const el = document.createElement("div");
  el.className = "item-card";
  el.innerHTML = `
    <div class="item-card-head">
      <strong>Featured ${i + 1}</strong>
      <button type="button" class="btn btn-danger btn-small" data-remove="project">Remove</button>
    </div>
    <div class="field"><label>Name</label><input data-k="name" value="${escapeHtml(item.name)}"></div>
    <div class="field"><label>Description</label><div data-rte-mount="description"></div></div>
    <div class="row-2">
      <div class="field"><label>Live URL (optional)</label><input data-k="liveUrl" value="${escapeHtml(item.liveUrl || "")}"></div>
      <div class="field"><label>Repo URL</label><input data-k="repoUrl" value="${escapeHtml(item.repoUrl || "")}"></div>
    </div>
    <div class="field"><label>Tags (comma-separated)</label><input data-k="tags" value="${escapeHtml((item.tags || []).join(", "))}"></div>
  `;
  mountRte(el, "description", item.description || "");
  return el;
}

function renderBooks() {
  const page = content.books;
  $("#books-eyebrow").value = page.eyebrow || "";
  $("#books-title").value = page.title || "";
  setStaticRte("books-lede", page.lede || "");
  const list = $("#books-list");
  list.innerHTML = "";
  (page.items || []).forEach((item, i) => list.appendChild(bookCard(item, i)));
}

function bookCard(item, i) {
  const el = document.createElement("div");
  el.className = "item-card";
  el.dataset.i = i;
  el.innerHTML = `
    <div class="item-card-head">
      <strong>Book ${i + 1}</strong>
      <button type="button" class="btn btn-danger btn-small" data-remove="book">Remove</button>
    </div>
    <div class="row-2">
      <div class="field"><label>Title</label><input data-k="title" value="${escapeHtml(item.title)}"></div>
      <div class="field"><label>Author</label><input data-k="author" value="${escapeHtml(item.author)}"></div>
    </div>
    <div class="row-2">
      <div class="field"><label>Rating (1–5)</label><input data-k="rating" type="number" min="1" max="5" value="${escapeHtml(item.rating)}"></div>
      <div class="field"><label>Cover path</label><input data-k="cover" value="${escapeHtml(item.cover || "")}"></div>
    </div>
    <div class="upload-row">
      <input type="file" accept="image/*" data-upload-folder="books">
      <button type="button" class="btn btn-ghost btn-small" data-upload-into="cover">Upload cover</button>
    </div>
    ${item.cover ? `<img class="thumb" src="${escapeHtml(item.cover)}" alt="">` : `<div class="thumb empty">Gradient cover</div>`}
    <div class="field"><label>Summary</label><div data-rte-mount="summary"></div></div>
  `;
  mountRte(el, "summary", item.summary || "");
  return el;
}

function renderMusings() {
  const page = content.musings;
  $("#musings-eyebrow").value = page.eyebrow || "";
  $("#musings-title").value = page.title || "";
  setStaticRte("musings-lede", page.lede || "");
  const list = $("#musings-list");
  list.innerHTML = "";
  (page.items || []).forEach((item, i) => list.appendChild(musingCard(item, i)));
}

function musingCard(item, i) {
  const el = document.createElement("div");
  el.className = "item-card";
  el.innerHTML = `
    <div class="item-card-head">
      <strong>Musing ${i + 1}</strong>
      <button type="button" class="btn btn-danger btn-small" data-remove="musing">Remove</button>
    </div>
    <div class="row-2">
      <div class="field"><label>Tag</label>
        <select data-k="tag">
          <option value="tech" ${item.tag === "tech" ? "selected" : ""}>tech</option>
          <option value="leadership" ${item.tag === "leadership" ? "selected" : ""}>leadership</option>
          <option value="life" ${item.tag === "life" ? "selected" : ""}>life</option>
        </select>
      </div>
      <div class="field"><label>Title</label><input data-k="title" value="${escapeHtml(item.title)}"></div>
    </div>
    <div class="field"><label>Body</label><div data-rte-mount="body"></div></div>
  `;
  mountRte(el, "body", item.body || "", { minHeight: "120px" });
  return el;
}

function renderArt() {
  const page = content.art;
  $("#art-eyebrow").value = page.eyebrow || "";
  $("#art-title").value = page.title || "";
  setStaticRte("art-lede", page.lede || "");
  const list = $("#art-list");
  list.innerHTML = "";
  (page.items || []).forEach((item, i) => list.appendChild(artCard(item, i)));
}

function artCard(item, i) {
  const el = document.createElement("div");
  el.className = "item-card";
  el.innerHTML = `
    <div class="item-card-head">
      <strong>Piece ${i + 1}</strong>
      <button type="button" class="btn btn-danger btn-small" data-remove="art">Remove</button>
    </div>
    <div class="field"><label>Title</label><input data-k="title" value="${escapeHtml(item.title)}"></div>
    <div class="row-2">
      <div class="field"><label>Image path</label><input data-k="image" value="${escapeHtml(item.image || "")}"></div>
      <div class="field"><label>Aspect ratio</label><input data-k="aspect" type="number" step="0.1" value="${escapeHtml(item.aspect ?? 1)}"></div>
    </div>
    <div class="upload-row">
      <input type="file" accept="image/*" data-upload-folder="art">
      <button type="button" class="btn btn-ghost btn-small" data-upload-into="image">Upload image</button>
    </div>
    ${item.image ? `<img class="thumb" src="${escapeHtml(item.image)}" alt="">` : `<div class="thumb empty">Gradient placeholder</div>`}
    <div class="field"><label>Summary</label><div data-rte-mount="summary"></div></div>
  `;
  mountRte(el, "summary", item.summary || "");
  return el;
}

function renderHiking() {
  const h = content.hiking;
  $("#hike-eyebrow").value = h.eyebrow || "";
  $("#hike-title").value = h.title || "";
  setStaticRte("hike-lede", h.lede || "");
  const stats = $("#hike-stats");
  stats.innerHTML = "";
  (h.stats || []).forEach((item, i) => stats.appendChild(statCard(item, i)));
  const trips = $("#hike-trips");
  trips.innerHTML = "";
  (h.trips || []).forEach((item, i) => trips.appendChild(tripCard(item, i)));
}

function statCard(item, i) {
  const el = document.createElement("div");
  el.className = "item-card";
  el.innerHTML = `
    <div class="item-card-head">
      <strong>Stat ${i + 1}</strong>
      <button type="button" class="btn btn-danger btn-small" data-remove="stat">Remove</button>
    </div>
    <div class="row-2">
      <div class="field"><label>Number</label><input data-k="num" type="number" value="${escapeHtml(item.num)}"></div>
      <div class="field"><label>Label</label><input data-k="label" value="${escapeHtml(item.label)}"></div>
    </div>
  `;
  return el;
}

function tripCard(item, i) {
  const el = document.createElement("div");
  el.className = "item-card";
  el.innerHTML = `
    <div class="item-card-head">
      <strong>Trip ${i + 1}</strong>
      <button type="button" class="btn btn-danger btn-small" data-remove="trip">Remove</button>
    </div>
    <div class="field"><label>Name</label><input data-k="name" value="${escapeHtml(item.name)}"></div>
    <div class="field"><label>Meta</label><input data-k="meta" value="${escapeHtml(item.meta)}"></div>
    <div class="field"><label>Photo path</label><input data-k="photo" value="${escapeHtml(item.photo || "")}"></div>
    <div class="upload-row">
      <input type="file" accept="image/*" data-upload-folder="hiking">
      <button type="button" class="btn btn-ghost btn-small" data-upload-into="photo">Upload photo</button>
    </div>
    ${item.photo ? `<img class="thumb" src="${escapeHtml(item.photo)}" alt="">` : `<div class="thumb empty">Gradient placeholder</div>`}
    <div class="field"><label>Story</label><div data-rte-mount="story"></div></div>
  `;
  mountRte(el, "story", item.story || "");
  return el;
}

function renderSite() {
  $("#site-brand").value = content.site?.brand || "";
  $("#site-email").value = content.site?.email || "";
}

function renderAll() {
  renderHome();
  renderBiography();
  renderEducation();
  renderAI();
  renderBooks();
  renderMusings();
  renderArt();
  renderHiking();
  renderSite();
}

function collectFromCards(container, mapFn) {
  return $$(".item-card", container).map(mapFn);
}

function gatherContent() {
  const highlights = collectFromCards($("#home-highlights"), card => {
    const slides = $$(".slide-item", card).map(el => el.dataset.src).filter(Boolean);
    return {
      num: $("[data-k=num]", card).value.trim(),
      title: $("[data-k=title]", card).value.trim(),
      text: getRteHtml(card, "text"),
      image: slides[0] || "",
      slides
    };
  });

  const career = collectFromCards($("#bio-career"), card => ({
    title: $("[data-k=title]", card).value.trim(),
    meta: $("[data-k=meta]", card).value.trim(),
    text: getRteHtml(card, "text"),
    attachments: $$(".attach-item", card).map(el => ({
      path: el.dataset.path,
      name: el.dataset.name,
      type: el.dataset.type
    }))
  }));

  const callouts = collectFromCards($("#bio-callouts"), card => ({
    title: $("[data-k=title]", card).value.trim(),
    text: getRteHtml(card, "text")
  }));

  const schools = collectFromCards($("#edu-schools"), card => ({
    title: $("[data-k=title]", card).value.trim(),
    meta: $("[data-k=meta]", card).value.trim(),
    blurb: getRteHtml(card, "blurb"),
    learned: getRteHtml(card, "learned")
  }));

  const gitProjects = collectFromCards($("#ai-git-projects"), card => ({
    name: $("[data-k=name]", card).value.trim(),
    summary: $("[data-k=summary]", card).value.trim(),
    image: $("[data-k=image]", card).value.trim(),
    repoUrl: $("[data-k=repoUrl]", card).value.trim()
  }));

  const projects = collectFromCards($("#ai-projects"), card => ({
    name: $("[data-k=name]", card).value.trim(),
    description: getRteHtml(card, "description"),
    liveUrl: $("[data-k=liveUrl]", card).value.trim(),
    repoUrl: $("[data-k=repoUrl]", card).value.trim(),
    tags: $("[data-k=tags]", card).value.split(",").map(s => s.trim()).filter(Boolean)
  }));

  const books = collectFromCards($("#books-list"), (card, idx) => {
    const existing = (content.books.items || [])[idx] || {};
    return {
      title: $("[data-k=title]", card).value.trim(),
      author: $("[data-k=author]", card).value.trim(),
      cover: $("[data-k=cover]", card).value.trim(),
      colors: existing.colors || ["#1f5f52", "#0a1f1a"],
      rating: Math.min(5, Math.max(1, parseInt($("[data-k=rating]", card).value, 10) || 3)),
      summary: getRteHtml(card, "summary")
    };
  });

  const musings = collectFromCards($("#musings-list"), card => ({
    tag: $("[data-k=tag]", card).value,
    title: $("[data-k=title]", card).value.trim(),
    body: getRteHtml(card, "body")
  }));

  const art = collectFromCards($("#art-list"), (card, idx) => {
    const existing = (content.art.items || [])[idx] || {};
    return {
      title: $("[data-k=title]", card).value.trim(),
      image: $("[data-k=image]", card).value.trim(),
      colors: existing.colors || ["#1f5f52", "#b5651d"],
      aspect: parseFloat($("[data-k=aspect]", card).value) || 1,
      summary: getRteHtml(card, "summary")
    };
  });

  const stats = collectFromCards($("#hike-stats"), card => ({
    num: parseInt($("[data-k=num]", card).value, 10) || 0,
    label: $("[data-k=label]", card).value.trim()
  }));

  const trips = collectFromCards($("#hike-trips"), (card, idx) => {
    const existing = content.hiking.trips[idx] || {};
    return {
      name: $("[data-k=name]", card).value.trim(),
      meta: $("[data-k=meta]", card).value.trim(),
      photo: $("[data-k=photo]", card).value.trim(),
      colors: existing.colors || ["#274b3e", "#6f8f45"],
      story: getRteHtml(card, "story")
    };
  });

  return {
    site: {
      brand: $("#site-brand").value.trim() || "Ishita",
      email: $("#site-email").value.trim()
    },
    home: {
      eyebrow: $("#home-eyebrow").value.trim(),
      headline: $("#home-headline").value.trim(),
      pitch: getStaticRte("home-pitch"),
      heroImage: $("#home-heroImage").value.trim(),
      heroLabel: $("#home-heroLabel").value.trim(),
      highlights
    },
    biography: {
      eyebrow: $("#bio-eyebrow").value.trim(),
      title: $("#bio-title").value.trim(),
      lede: getStaticRte("bio-lede"),
      summary: getStaticRte("bio-summary"),
      career,
      callouts
    },
    education: {
      eyebrow: $("#edu-eyebrow").value.trim(),
      title: $("#edu-title").value.trim(),
      lede: getStaticRte("edu-lede"),
      schools
    },
    aiJourney: {
      eyebrow: $("#ai-eyebrow").value.trim(),
      title: $("#ai-title").value.trim(),
      lede: getStaticRte("ai-lede"),
      story: getStaticRte("ai-story"),
      githubUsername: $("#ai-github").value.trim(),
      gitProjects,
      projects
    },
    books: {
      eyebrow: $("#books-eyebrow").value.trim(),
      title: $("#books-title").value.trim(),
      lede: getStaticRte("books-lede"),
      items: books
    },
    musings: {
      eyebrow: $("#musings-eyebrow").value.trim(),
      title: $("#musings-title").value.trim(),
      lede: getStaticRte("musings-lede"),
      items: musings
    },
    art: {
      eyebrow: $("#art-eyebrow").value.trim(),
      title: $("#art-title").value.trim(),
      lede: getStaticRte("art-lede"),
      items: art
    },
    hiking: {
      eyebrow: $("#hike-eyebrow").value.trim(),
      title: $("#hike-title").value.trim(),
      lede: getStaticRte("hike-lede"),
      stats,
      trips
    }
  };
}

async function requireAuthOrRedirect(res, data) {
  if (res.status === 401 || (data && data.error === "Unauthorized")) {
    setStatus("Session expired — sign in again", "error");
    setTimeout(() => {
      location.href = "login.html?next=admin.html";
    }, 700);
    return true;
  }
  return false;
}

async function saveAll() {
  try {
    content = gatherContent();
    setStatus("Saving…");
    const res = await fetch("/api/content", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(content)
    });
    const data = await res.json().catch(() => ({}));
    if (await requireAuthOrRedirect(res, data)) return;
    if (!res.ok || !data.ok) throw new Error(data.error || "Save failed");
    setStatus("Saved", "ok");
    renderAll();
  } catch (err) {
    setStatus(err.message || "Save failed", "error");
  }
}

function bindActions() {
  $("#save-btn").addEventListener("click", saveAll);
  $("#logout-btn")?.addEventListener("click", async () => {
    await fetch("/api/logout", { method: "POST", credentials: "same-origin" });
    location.href = "index.html";
  });
  $("#home-heroImage").addEventListener("input", updateHeroPreview);

  $("[data-upload=home-hero]").addEventListener("click", async () => {
    const file = $("#home-hero-file").files[0];
    if (!file) return setStatus("Choose a photo first", "error");
    try {
      setStatus("Uploading…");
      const uploaded = await uploadFile(file, "hero");
      $("#home-heroImage").value = uploaded.path || uploaded;
      updateHeroPreview();
      setStatus("Photo uploaded — click Save", "ok");
    } catch (err) {
      setStatus(err.message, "error");
    }
  });

  $("#add-highlight").addEventListener("click", () => {
    content.home.highlights.push({ num: "0", title: "New pillar", text: "", image: "", slides: [] });
    renderHome();
  });
  $("#add-career").addEventListener("click", () => {
    content.biography.career.push({ title: "New role", meta: "", text: "", attachments: [] });
    renderBiography();
  });
  $("#add-callout").addEventListener("click", () => {
    content.biography.callouts.push({ title: "New callout", text: "" });
    renderBiography();
  });
  $("#add-school").addEventListener("click", () => {
    content.education.schools.push({ title: "New school", meta: "", blurb: "", learned: "" });
    renderEducation();
  });
  $("#add-git-project").addEventListener("click", () => {
    content.aiJourney.gitProjects = content.aiJourney.gitProjects || [];
    content.aiJourney.gitProjects.push({ name: "New Git project", summary: "", image: "", repoUrl: "" });
    renderAI();
  });
  $("#add-project").addEventListener("click", () => {
    content.aiJourney.projects.push({ name: "New project", description: "", liveUrl: "", repoUrl: "", tags: [] });
    renderAI();
  });
  $("#add-book").addEventListener("click", () => {
    content.books.items.push({ title: "New book", author: "", cover: "", colors: ["#1f5f52", "#0a1f1a"], rating: 4, summary: "" });
    renderBooks();
  });
  $("#add-musing").addEventListener("click", () => {
    content.musings.items.push({ tag: "tech", title: "New musing", body: "" });
    renderMusings();
  });
  $("#add-art").addEventListener("click", () => {
    content.art.items.push({ title: "New piece", image: "", colors: ["#1f5f52", "#b5651d"], aspect: 1, summary: "" });
    renderArt();
  });
  $("#add-stat").addEventListener("click", () => {
    content.hiking.stats.push({ num: 0, label: "New stat" });
    renderHiking();
  });
  $("#add-trip").addEventListener("click", () => {
    content.hiking.trips.push({ name: "New trail", meta: "", photo: "", colors: ["#274b3e", "#6f8f45"], story: "" });
    renderHiking();
  });

  document.addEventListener("click", async e => {
    const removeSlide = e.target.closest("[data-remove-slide]");
    if (removeSlide) {
      content = gatherContent();
      const card = removeSlide.closest(".item-card");
      const slideItem = removeSlide.closest(".slide-item");
      const parent = card.parentElement;
      const idx = [...parent.children].indexOf(card);
      const slideIdx = [...card.querySelectorAll(".slide-item")].indexOf(slideItem);
      if (idx >= 0 && content.home.highlights[idx]) {
        const slides = content.home.highlights[idx].slides || [];
        slides.splice(slideIdx, 1);
        content.home.highlights[idx].slides = slides;
        content.home.highlights[idx].image = slides[0] || "";
      }
      renderAll();
      return;
    }

    const removeAttach = e.target.closest("[data-remove-attach]");
    if (removeAttach) {
      content = gatherContent();
      const card = removeAttach.closest(".item-card");
      const item = removeAttach.closest(".attach-item");
      const parent = card.parentElement;
      const idx = [...parent.children].indexOf(card);
      const aIdx = [...card.querySelectorAll(".attach-item")].indexOf(item);
      if (idx >= 0 && content.biography.career[idx]) {
        const list = content.biography.career[idx].attachments || [];
        list.splice(aIdx, 1);
        content.biography.career[idx].attachments = list;
      }
      renderAll();
      return;
    }

    const addRoleFiles = e.target.closest("[data-add-role-files]");
    if (addRoleFiles) {
      const card = addRoleFiles.closest(".item-card");
      const fileInput = $("input[type=file]", card);
      const files = [...(fileInput?.files || [])];
      if (!files.length) return setStatus("Choose one or more files first", "error");
      try {
        setStatus("Uploading files…");
        content = gatherContent();
        const parent = card.parentElement;
        const idx = [...parent.children].indexOf(card);
        const role = content.biography.career[idx];
        if (!role) throw new Error("Role not found");
        role.attachments = role.attachments || [];
        for (const file of files) {
          const uploaded = await uploadFile(file, "roles");
          role.attachments.push({
            path: uploaded.path || uploaded,
            name: uploaded.name || file.name,
            type: uploaded.type || (file.name.split(".").pop() || "")
          });
        }
        renderAll();
        setStatus(`Uploaded ${files.length} file(s) — click Save`, "ok");
      } catch (err) {
        setStatus(err.message, "error");
      }
      return;
    }

    const addSlidesBtn = e.target.closest("[data-add-pillar-slides]");
    if (addSlidesBtn) {
      const card = addSlidesBtn.closest(".item-card");
      const fileInput = $("input[type=file]", card);
      const files = [...(fileInput?.files || [])];
      if (!files.length) return setStatus("Choose one or more images first", "error");
      try {
        setStatus("Uploading slides…");
        content = gatherContent();
        const parent = card.parentElement;
        const idx = [...parent.children].indexOf(card);
        const pillar = content.home.highlights[idx];
        if (!pillar) throw new Error("Pillar not found");
        pillar.slides = pillar.slides || [];
        for (const file of files) {
          const uploaded = await uploadFile(file, "pillars");
          pillar.slides.push(uploaded.path || uploaded);
        }
        pillar.image = pillar.slides[0] || "";
        renderAll();
        setStatus(`Uploaded ${files.length} slide(s) — click Save`, "ok");
      } catch (err) {
        setStatus(err.message, "error");
      }
      return;
    }

    const removeBtn = e.target.closest("[data-remove]");
    if (removeBtn) {
      // Flush current edits into content first
      content = gatherContent();
      const kind = removeBtn.dataset.remove;
      const card = removeBtn.closest(".item-card");
      const parent = card.parentElement;
      const idx = [...parent.children].indexOf(card);
      const map = {
        highlight: () => content.home.highlights.splice(idx, 1),
        career: () => content.biography.career.splice(idx, 1),
        callout: () => content.biography.callouts.splice(idx, 1),
        school: () => content.education.schools.splice(idx, 1),
        gitProject: () => content.aiJourney.gitProjects.splice(idx, 1),
        project: () => content.aiJourney.projects.splice(idx, 1),
        book: () => content.books.items.splice(idx, 1),
        musing: () => content.musings.items.splice(idx, 1),
        art: () => content.art.items.splice(idx, 1),
        stat: () => content.hiking.stats.splice(idx, 1),
        trip: () => content.hiking.trips.splice(idx, 1)
      };
      map[kind]?.();
      renderAll();
      return;
    }

    const uploadBtn = e.target.closest("[data-upload-into]");
    if (uploadBtn) {
      const card = uploadBtn.closest(".item-card");
      const fileInput = $("input[type=file]", card);
      const folder = fileInput?.dataset.uploadFolder;
      const field = uploadBtn.dataset.uploadInto;
      if (!fileInput?.files?.[0]) return setStatus("Choose a file first", "error");
      try {
        setStatus("Uploading…");
        const uploaded = await uploadFile(fileInput.files[0], folder);
        $(`[data-k=${field}]`, card).value = uploaded.path || uploaded;
        content = gatherContent();
        renderAll();
        setStatus("Uploaded — click Save", "ok");
      } catch (err) {
        setStatus(err.message, "error");
      }
    }
  });
}

async function init() {
  bindNav();
  bindActions();
  try {
    const sessionRes = await fetch("/api/session", { credentials: "same-origin" });
    const session = await sessionRes.json();
    if (!session.authenticated) {
      location.href = "login.html?next=admin.html";
      return;
    }
    const res = await fetch("/api/content", { credentials: "same-origin" });
    if (!res.ok) throw new Error("Could not load content");
    content = normalizeContent(await res.json());
    renderAll();
    setStatus(`Signed in as ${session.email}`, "ok");
  } catch (err) {
    setStatus(err.message, "error");
  }
}

init();
