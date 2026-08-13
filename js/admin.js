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
  c.site = c.site || {};
  c.books = normalizeListPage(c.books, {
    eyebrow: "Beyond Technology / Books",
    title: "What I'm Reading",
    lede: "<p>Click a cover to flip it over for the summary.</p>"
  });
  c.musings = normalizeListPage(c.musings, {
    eyebrow: "Perspectives",
    title: "Featured perspectives",
    lede: "<p>Short theses on AI transformation, data platforms, and leadership.</p>"
  });
  c.art = normalizeListPage(c.art, {
    eyebrow: "Beyond Technology / Art",
    title: "My Art",
    lede: "<p>A portfolio in progress. Click any piece for the full story behind it.</p>"
  });
  c.biography = c.biography || {};
  c.biography.bios = c.biography.bios || { short: "", medium: "", full: "" };
  if (!Array.isArray(c.biography.career)) c.biography.career = [];
  if (!Array.isArray(c.biography.callouts)) c.biography.callouts = [];
  if (!Array.isArray(c.biography.recognition)) c.biography.recognition = c.biography.callouts.slice();
  if (c.biography.quote == null) {
    c.biography.quote = "Technology creates value only when people can trust it, use it, and act on it";
  }
  if (c.biography.builder == null) c.biography.builder = "";
  c.education = c.education || {};
  c.aiJourney = c.aiJourney || {};
  c.aiLab = c.aiLab || { eyebrow: "AI Lab", title: "Recent builds", lede: "", items: [] };
  if (!Array.isArray(c.aiLab.items)) c.aiLab.items = [];
  c.hiking = c.hiking || {};
  c.speaking = c.speaking || { eyebrow: "Speaking", title: "Speaking & conversations", lede: "", items: [] };
  if (!Array.isArray(c.speaking.items)) c.speaking.items = [];
  c.impact = c.impact || { eyebrow: "Impact", title: "Selected impact", lede: "", items: [] };
  if (!Array.isArray(c.impact.items)) c.impact.items = c.home?.selectedImpact || [];
  c.home = c.home || {};
  if (!Array.isArray(c.home.proofMetrics)) c.home.proofMetrics = [];
  if (!Array.isArray(c.home.whatIDo)) c.home.whatIDo = [];
  if (!Array.isArray(c.home.selectedImpact)) c.home.selectedImpact = c.impact.items || [];
  if (!Array.isArray(c.home.careerArc)) c.home.careerArc = [];
  if (!Array.isArray(c.home.beliefs)) c.home.beliefs = [];
  if (!Array.isArray(c.home.featuredPerspectives)) c.home.featuredPerspectives = [];
  if (!Array.isArray(c.home.highlights)) c.home.highlights = [];
  if (!c.biography.title) c.biography.title = "Ishita Majumdar";
  if (!c.biography.eyebrow) c.biography.eyebrow = "About";
  if (!c.education.title) c.education.title = "How I Learned";
  if (!c.education.eyebrow) c.education.eyebrow = "02 / Education";
  if (!c.aiJourney.title) c.aiJourney.title = "Building in public";
  if (!c.aiJourney.eyebrow) c.aiJourney.eyebrow = "AI Lab";
  if (!Array.isArray(c.aiJourney.gitProjects)) c.aiJourney.gitProjects = [];
  if (!Array.isArray(c.aiJourney.featuredBuilds)) {
    const legacy = Array.isArray(c.aiJourney.projects) ? c.aiJourney.projects : [];
    c.aiJourney.featuredBuilds = legacy.map(p => {
      const raw = p.summary || p.description || "";
      const summary = String(raw).replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
      return {
        name: p.name || "",
        summary,
        image: p.image || "",
        liveUrl: p.liveUrl || ""
      };
    });
  }
  if (!Array.isArray(c.aiJourney.projects)) c.aiJourney.projects = [];
  if (!c.hiking.title) c.hiking.title = "On the Trail";
  if (!c.hiking.eyebrow) c.hiking.eyebrow = "Beyond Technology / Trails";
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
  if ($("#home-name")) $("#home-name").value = h.name || "";
  $("#home-headline").value = h.headline || "";
  setStaticRte("home-pitch", h.pitch || "", { minHeight: "120px" });
  $("#home-heroImage").value = h.heroImage || "";
  $("#home-heroLabel").value = h.heroLabel || "";
  updateHeroPreview();

  const proof = $("#home-proof");
  if (proof) {
    proof.innerHTML = "";
    (h.proofMetrics || []).forEach((item, i) => {
      const el = document.createElement("div");
      el.className = "item-card";
      el.innerHTML = `
        <div class="item-card-head"><strong>Metric ${i + 1}</strong>
          <button type="button" class="btn btn-danger btn-small" data-remove="proof">Remove</button></div>
        <div class="row-2">
          <div class="field"><label>Value</label><input data-k="value" value="${escapeHtml(item.value || "")}"></div>
          <div class="field"><label>Label</label><input data-k="label" value="${escapeHtml(item.label || "")}"></div>
        </div>`;
      proof.appendChild(el);
    });
  }

  const what = $("#home-whatido");
  if (what) {
    what.innerHTML = "";
    (h.whatIDo || []).forEach((item, i) => {
      const el = document.createElement("div");
      el.className = "item-card";
      el.innerHTML = `
        <div class="item-card-head"><strong>Pillar ${i + 1}</strong>
          <button type="button" class="btn btn-danger btn-small" data-remove="whatido">Remove</button></div>
        <div class="field"><label>Title</label><input data-k="title" value="${escapeHtml(item.title || "")}"></div>
        <div class="field"><label>Text</label><textarea data-k="text" rows="3">${escapeHtml(item.text || "")}</textarea></div>
        <div class="field"><label>Image path</label><input data-k="image" value="${escapeHtml(item.image || "")}" placeholder="images/pillars/..."></div>
        <div class="upload-row">
          <input type="file" accept="image/jpeg,image/jpg,image/png,image/webp,image/gif" data-upload-folder="pillars">
          <button type="button" class="btn btn-ghost btn-small" data-upload-whatido-image>Upload image</button>
        </div>
        ${item.image ? `<img class="thumb" src="${escapeHtml(item.image)}" alt="">` : `<div class="thumb empty">No image</div>`}`;
      what.appendChild(el);
    });
  }

  const arc = $("#home-career-arc");
  if (arc) {
    arc.innerHTML = "";
    (h.careerArc || []).forEach((item, i) => {
      const el = document.createElement("div");
      el.className = "item-card";
      el.innerHTML = `
        <div class="item-card-head"><strong>Stage ${i + 1}</strong>
          <button type="button" class="btn btn-danger btn-small" data-remove="careerArc">Remove</button></div>
        <div class="row-2">
          <div class="field"><label>Stage</label><input data-k="stage" value="${escapeHtml(item.stage || "")}"></div>
          <div class="field"><label>Detail</label><input data-k="detail" value="${escapeHtml(item.detail || "")}"></div>
        </div>`;
      arc.appendChild(el);
    });
  }

  const beliefs = $("#home-beliefs");
  if (beliefs) {
    beliefs.innerHTML = "";
    (h.beliefs || []).forEach((item, i) => {
      const el = document.createElement("div");
      el.className = "item-card";
      el.innerHTML = `
        <div class="item-card-head"><strong>Belief ${i + 1}</strong>
          <button type="button" class="btn btn-danger btn-small" data-remove="belief">Remove</button></div>
        <div class="field"><label>Title</label><input data-k="title" value="${escapeHtml(item.title || "")}"></div>
        <div class="field"><label>Text</label><textarea data-k="text" rows="3">${escapeHtml(item.text || "")}</textarea></div>
        <div class="row-2">
          <div class="field"><label>Link</label><input data-k="link" value="${escapeHtml(item.link || "")}"></div>
          <div class="field"><label>Link label</label><input data-k="linkLabel" value="${escapeHtml(item.linkLabel || "")}"></div>
        </div>`;
      beliefs.appendChild(el);
    });
  }

  const list = $("#home-highlights");
  if (list) {
    list.innerHTML = "";
    (h.highlights || []).forEach((item, i) => {
      list.appendChild(highlightCard(item, i));
    });
  }
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
  if ($("#bio-quote")) $("#bio-quote").value = b.quote || "";
  if ($("#bio-short")) $("#bio-short").value = b.bios?.short || "";
  if ($("#bio-medium")) $("#bio-medium").value = b.bios?.medium || "";
  setStaticRte("bio-summary", paragraphsToHtml(b.summary || b.bios?.full || ""), { minHeight: "160px" });
  setStaticRte("bio-builder", paragraphsToHtml(b.builder || ""), { minHeight: "120px" });
  if ($("#bio-headshot")) $("#bio-headshot").value = b.headshot || "";
  if ($("#bio-download")) $("#bio-download").value = b.bioDownload || "";
  const career = $("#bio-career");
  career.innerHTML = "";
  (b.career || []).forEach((item, i) => career.appendChild(careerCard(item, i)));
  const callouts = $("#bio-callouts");
  callouts.innerHTML = "";
  const recognition = Array.isArray(b.recognition) && b.recognition.length
    ? b.recognition
    : (b.callouts || []);
  recognition.forEach((item, i) => callouts.appendChild(calloutCard(item, i)));
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
      <strong>Recognition ${i + 1}</strong>
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
  const buildsList = $("#ai-featured-builds");
  buildsList.innerHTML = "";
  (a.featuredBuilds || []).forEach((item, i) => buildsList.appendChild(featuredBuildCard(item, i)));
  const labList = $("#ai-lab-items");
  if (labList) {
    labList.innerHTML = "";
    (content.aiLab?.items || []).forEach((item, i) => labList.appendChild(labItemCard(item, i)));
  }
}

function labItemCard(item, i) {
  const el = document.createElement("div");
  el.className = "item-card";
  el.innerHTML = `
    <div class="item-card-head">
      <strong>Lab item ${i + 1}</strong>
      <button type="button" class="btn btn-danger btn-small" data-remove="labItem">Remove</button>
    </div>
    <div class="field"><label>Name</label><input data-k="name" value="${escapeHtml(item.name || "")}"></div>
    <div class="field"><label>Summary</label><textarea data-k="summary" rows="2">${escapeHtml(item.summary || "")}</textarea></div>
    <div class="field"><label>Why built</label><textarea data-k="why" rows="2">${escapeHtml(item.why || "")}</textarea></div>
    <div class="field"><label>Tech</label><input data-k="tech" value="${escapeHtml(item.tech || "")}"></div>
    <div class="field"><label>Learned</label><textarea data-k="learned" rows="2">${escapeHtml(item.learned || "")}</textarea></div>
    <div class="field"><label>Image</label><input data-k="image" value="${escapeHtml(item.image || "")}"></div>
    <div class="row-2">
      <div class="field"><label>Live URL</label><input data-k="liveUrl" value="${escapeHtml(item.liveUrl || "")}"></div>
      <div class="field"><label>Repo URL</label><input data-k="repoUrl" value="${escapeHtml(item.repoUrl || "")}"></div>
    </div>
  `;
  return el;
}

function renderImpact() {
  const list = $("#impact-list");
  if (!list) return;
  list.innerHTML = "";
  const items = content.impact?.items || content.home?.selectedImpact || [];
  items.forEach((item, i) => {
    const el = document.createElement("div");
    el.className = "item-card";
    el.innerHTML = `
      <div class="item-card-head"><strong>Case ${i + 1}</strong>
        <button type="button" class="btn btn-danger btn-small" data-remove="impact">Remove</button></div>
      <div class="row-2">
        <div class="field"><label>Org</label><input data-k="org" value="${escapeHtml(item.org || "")}"></div>
        <div class="field"><label>Title</label><input data-k="title" value="${escapeHtml(item.title || "")}"></div>
      </div>
      <div class="field"><label>Cover image path</label><input data-k="image" value="${escapeHtml(item.image || "")}" placeholder="images/impact/..."></div>
      <div class="upload-row">
        <input type="file" accept="image/jpeg,image/jpg,image/png,image/webp,image/gif" data-upload-folder="impact">
        <button type="button" class="btn btn-ghost btn-small" data-upload-into="image">Upload cover</button>
      </div>
      ${item.image ? `<img class="thumb" src="${escapeHtml(item.image)}" alt="">` : `<div class="thumb empty">No cover yet</div>`}
      <div class="field"><label>Challenge</label><textarea data-k="challenge" rows="3">${escapeHtml(item.challenge || "")}</textarea></div>
      <div class="field"><label>Built / Action</label><textarea data-k="action" rows="3">${escapeHtml(item.action || "")}</textarea></div>
      <div class="field"><label>Impact</label><textarea data-k="impact" rows="3">${escapeHtml(item.impact || "")}</textarea></div>`;
    list.appendChild(el);
  });
}

function renderSpeaking() {
  if ($("#speaking-eyebrow")) $("#speaking-eyebrow").value = content.speaking?.eyebrow || "";
  if ($("#speaking-title")) $("#speaking-title").value = content.speaking?.title || "";
  if ($("#speaking-lede")) setStaticRte("speaking-lede", content.speaking?.lede || "");
  const list = $("#speaking-list");
  if (!list) return;
  list.innerHTML = "";
  (content.speaking?.items || []).forEach((item, i) => {
    const el = document.createElement("div");
    el.className = "item-card";
    el.innerHTML = `
      <div class="item-card-head"><strong>Talk ${i + 1}</strong>
        <button type="button" class="btn btn-danger btn-small" data-remove="speaking">Remove</button></div>
      <div class="field"><label>Title</label><input data-k="title" value="${escapeHtml(item.title || "")}"></div>
      <div class="row-2">
        <div class="field"><label>Event</label><input data-k="event" value="${escapeHtml(item.event || "")}"></div>
        <div class="field"><label>Meta</label><input data-k="meta" value="${escapeHtml(item.meta || "")}"></div>
      </div>
      <div class="field"><label>Blurb</label><textarea data-k="blurb" rows="3">${escapeHtml(item.blurb || "")}</textarea></div>
      <div class="field"><label>Link</label><input data-k="link" value="${escapeHtml(item.link || "")}"></div>`;
    list.appendChild(el);
  });
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

function featuredBuildCard(item, i) {
  const el = document.createElement("div");
  el.className = "item-card";
  el.innerHTML = `
    <div class="item-card-head">
      <strong>Featured build ${i + 1}</strong>
      <button type="button" class="btn btn-danger btn-small" data-remove="featuredBuild">Remove</button>
    </div>
    <div class="field"><label>Name</label><input data-k="name" value="${escapeHtml(item.name || "")}"></div>
    <div class="field"><label>Summary</label><textarea data-k="summary" rows="3">${escapeHtml(item.summary || "")}</textarea></div>
    <div class="field"><label>Cover image path</label><input data-k="image" value="${escapeHtml(item.image || "")}"></div>
    <div class="upload-row">
      <input type="file" accept="image/*" data-upload-folder="builds">
      <button type="button" class="btn btn-ghost btn-small" data-upload-into="image">Upload cover</button>
    </div>
    ${item.image ? `<img class="thumb" src="${escapeHtml(item.image)}" alt="">` : `<div class="thumb empty">No cover yet</div>`}
    <div class="field"><label>Public live URL (Railway)</label><input data-k="liveUrl" placeholder="https://….up.railway.app" value="${escapeHtml(item.liveUrl || "")}"></div>
  `;
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
  if ($("#site-tagline")) $("#site-tagline").value = content.site?.tagline || "";
  if ($("#site-linkedin")) $("#site-linkedin").value = content.site?.linkedin || "";
  if ($("#site-github")) $("#site-github").value = content.site?.github || "";
}

function renderAll() {
  renderHome();
  renderImpact();
  renderBiography();
  renderEducation();
  renderAI();
  renderBooks();
  renderMusings();
  renderSpeaking();
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

  const featuredBuilds = collectFromCards($("#ai-featured-builds"), card => ({
    name: $("[data-k=name]", card).value.trim(),
    summary: $("[data-k=summary]", card).value.trim(),
    image: $("[data-k=image]", card).value.trim(),
    liveUrl: $("[data-k=liveUrl]", card).value.trim()
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

  const proofMetrics = $("#home-proof")
    ? collectFromCards($("#home-proof"), card => ({
        value: $("[data-k=value]", card).value.trim(),
        label: $("[data-k=label]", card).value.trim()
      }))
    : (content.home.proofMetrics || []);

  const whatIDo = $("#home-whatido")
    ? collectFromCards($("#home-whatido"), card => ({
        title: $("[data-k=title]", card).value.trim(),
        text: $("[data-k=text]", card).value.trim(),
        image: $("[data-k=image]", card)?.value.trim() || ""
      }))
    : (content.home.whatIDo || []);

  const careerArc = $("#home-career-arc")
    ? collectFromCards($("#home-career-arc"), card => ({
        stage: $("[data-k=stage]", card).value.trim(),
        detail: $("[data-k=detail]", card).value.trim()
      }))
    : (content.home.careerArc || []);

  const beliefs = $("#home-beliefs")
    ? collectFromCards($("#home-beliefs"), card => ({
        title: $("[data-k=title]", card).value.trim(),
        text: $("[data-k=text]", card).value.trim(),
        link: $("[data-k=link]", card).value.trim(),
        linkLabel: $("[data-k=linkLabel]", card).value.trim()
      }))
    : (content.home.beliefs || []);

  const selectedImpact = $("#impact-list")
    ? collectFromCards($("#impact-list"), card => ({
        org: $("[data-k=org]", card).value.trim(),
        title: $("[data-k=title]", card).value.trim(),
        challenge: $("[data-k=challenge]", card).value.trim(),
        action: $("[data-k=action]", card).value.trim(),
        impact: $("[data-k=impact]", card).value.trim(),
        image: $("[data-k=image]", card).value.trim()
      }))
    : (content.home.selectedImpact || content.impact?.items || []);

  const labItems = $("#ai-lab-items")
    ? collectFromCards($("#ai-lab-items"), card => ({
        name: $("[data-k=name]", card).value.trim(),
        summary: $("[data-k=summary]", card).value.trim(),
        why: $("[data-k=why]", card).value.trim(),
        tech: $("[data-k=tech]", card).value.trim(),
        learned: $("[data-k=learned]", card).value.trim(),
        image: $("[data-k=image]", card).value.trim(),
        liveUrl: $("[data-k=liveUrl]", card).value.trim(),
        repoUrl: $("[data-k=repoUrl]", card).value.trim()
      }))
    : (content.aiLab?.items || []);

  const speakingItems = $("#speaking-list")
    ? collectFromCards($("#speaking-list"), card => ({
        title: $("[data-k=title]", card).value.trim(),
        event: $("[data-k=event]", card).value.trim(),
        meta: $("[data-k=meta]", card).value.trim(),
        blurb: $("[data-k=blurb]", card).value.trim(),
        link: $("[data-k=link]", card).value.trim()
      }))
    : (content.speaking?.items || []);

  const fullBio = getStaticRte("bio-summary");

  return {
    site: {
      brand: $("#site-brand").value.trim() || "Ishita Majumdar",
      email: $("#site-email").value.trim(),
      tagline: ($("#site-tagline")?.value || content.site?.tagline || "Technology • Data • AI • Transformation").trim(),
      linkedin: ($("#site-linkedin")?.value || content.site?.linkedin || "").trim(),
      github: ($("#site-github")?.value || content.site?.github || "imajumd1").trim()
    },
    home: {
      eyebrow: $("#home-eyebrow").value.trim(),
      name: ($("#home-name")?.value || content.home.name || "Ishita Majumdar").trim(),
      headline: $("#home-headline").value.trim(),
      pitch: getStaticRte("home-pitch"),
      heroImage: $("#home-heroImage").value.trim(),
      heroLabel: $("#home-heroLabel").value.trim(),
      ctaPrimary: content.home.ctaPrimary || { label: "Beliefs that shape my work", href: "biography.html#how-i-think" },
      ctaSecondary: content.home.ctaSecondary || { label: "Building with AI", href: "ai-journey.html" },
      ctaLinkedIn: content.home.ctaLinkedIn || {},
      proofMetrics,
      whatIDo,
      selectedImpact,
      careerArc,
      beliefs,
      featuredPerspectives: content.home.featuredPerspectives || [],
      highlights
    },
    impact: {
      eyebrow: content.impact?.eyebrow || "Impact",
      title: content.impact?.title || "Selected impact",
      lede: content.impact?.lede || "",
      items: selectedImpact
    },
    biography: {
      eyebrow: $("#bio-eyebrow").value.trim(),
      title: $("#bio-title").value.trim(),
      lede: getStaticRte("bio-lede"),
      quote: ($("#bio-quote")?.value || content.biography?.quote || "").trim(),
      summary: fullBio,
      builder: getStaticRte("bio-builder") || content.biography?.builder || "",
      bios: {
        short: ($("#bio-short")?.value || content.biography?.bios?.short || "").trim(),
        medium: ($("#bio-medium")?.value || content.biography?.bios?.medium || "").trim(),
        full: fullBio
      },
      headshot: ($("#bio-headshot")?.value || content.biography?.headshot || "").trim(),
      bioDownload: ($("#bio-download")?.value || content.biography?.bioDownload || "").trim(),
      career,
      callouts,
      recognition: callouts
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
      featuredBuilds,
      projects: content.aiJourney.projects || []
    },
    aiLab: {
      eyebrow: content.aiLab?.eyebrow || "AI Lab",
      title: content.aiLab?.title || "Recent builds",
      lede: content.aiLab?.lede || "",
      items: labItems
    },
    speaking: {
      eyebrow: ($("#speaking-eyebrow")?.value || content.speaking?.eyebrow || "Speaking").trim(),
      title: ($("#speaking-title")?.value || content.speaking?.title || "Speaking & conversations").trim(),
      lede: $("#speaking-lede") ? getStaticRte("speaking-lede") : (content.speaking?.lede || ""),
      items: speakingItems
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
      items: musings.map((m, idx) => {
        const prev = (content.musings.items || [])[idx] || {};
        return {
          ...m,
          category: prev.category || "",
          thesis: prev.thesis || "",
          readingTime: prev.readingTime || "",
          date: prev.date || ""
        };
      })
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
    content.home.highlights = content.home.highlights || [];
    content.home.highlights.push({ num: "0", title: "New pillar", text: "", image: "", slides: [] });
    renderHome();
  });
  $("#add-proof")?.addEventListener("click", () => {
    content.home.proofMetrics = content.home.proofMetrics || [];
    content.home.proofMetrics.push({ value: "", label: "" });
    renderHome();
  });
  $("#add-whatido")?.addEventListener("click", () => {
    content.home.whatIDo = content.home.whatIDo || [];
    content.home.whatIDo.push({ title: "New pillar", text: "", image: "" });
    renderHome();
  });
  $("#add-career-arc")?.addEventListener("click", () => {
    content.home.careerArc = content.home.careerArc || [];
    content.home.careerArc.push({ stage: "New stage", detail: "" });
    renderHome();
  });
  $("#add-belief")?.addEventListener("click", () => {
    content.home.beliefs = content.home.beliefs || [];
    content.home.beliefs.push({ title: "New belief", text: "", link: "", linkLabel: "" });
    renderHome();
  });
  $("#add-impact")?.addEventListener("click", () => {
    content.impact = content.impact || { items: [] };
    content.impact.items = content.impact.items || [];
    content.impact.items.push({ org: "", title: "New case study", challenge: "", action: "", impact: "", image: "" });
    content.home.selectedImpact = content.impact.items;
    renderImpact();
  });
  $("#add-career").addEventListener("click", () => {
    content.biography.career.push({ title: "New role", meta: "", text: "", attachments: [] });
    renderBiography();
  });
  $("#add-callout").addEventListener("click", () => {
    content.biography.callouts.push({ title: "New recognition", text: "" });
    content.biography.recognition = content.biography.callouts;
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
  $("#add-featured-build").addEventListener("click", () => {
    content.aiJourney.featuredBuilds = content.aiJourney.featuredBuilds || [];
    content.aiJourney.featuredBuilds.push({ name: "New featured build", summary: "", image: "", liveUrl: "" });
    renderAI();
  });
  $("#add-lab-item")?.addEventListener("click", () => {
    content.aiLab = content.aiLab || { items: [] };
    content.aiLab.items = content.aiLab.items || [];
    content.aiLab.items.push({ name: "New build", summary: "", why: "", tech: "", learned: "", image: "", liveUrl: "", repoUrl: "" });
    renderAI();
  });
  $("#add-speaking")?.addEventListener("click", () => {
    content.speaking = content.speaking || { items: [] };
    content.speaking.items = content.speaking.items || [];
    content.speaking.items.push({ title: "New talk", event: "", meta: "", blurb: "", link: "" });
    renderSpeaking();
  });
  $("#add-book").addEventListener("click", () => {
    content.books.items.push({ title: "New book", author: "", cover: "", colors: ["#1f5f52", "#0a1f1a"], rating: 4, summary: "" });
    renderBooks();
  });
  $("#add-musing").addEventListener("click", () => {
    content.musings.items.push({ tag: "tech", title: "New perspective", body: "", category: "AI & Enterprise Transformation" });
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

    const uploadWhatIdo = e.target.closest("[data-upload-whatido-image]");
    if (uploadWhatIdo) {
      const card = uploadWhatIdo.closest(".item-card");
      const fileInput = $("input[type=file]", card);
      const file = fileInput?.files?.[0];
      if (!file) return setStatus("Choose an image first", "error");
      try {
        setStatus("Uploading image…");
        content = gatherContent();
        const parent = card.parentElement;
        const idx = [...parent.children].indexOf(card);
        const pillar = content.home.whatIDo[idx];
        if (!pillar) throw new Error("Pillar not found");
        const uploaded = await uploadFile(file, "pillars");
        pillar.image = uploaded.path || uploaded;
        renderAll();
        setStatus("Image uploaded — click Save", "ok");
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
        proof: () => content.home.proofMetrics.splice(idx, 1),
        whatido: () => content.home.whatIDo.splice(idx, 1),
        careerArc: () => content.home.careerArc.splice(idx, 1),
        belief: () => content.home.beliefs.splice(idx, 1),
        impact: () => {
          (content.impact.items || content.home.selectedImpact).splice(idx, 1);
          content.home.selectedImpact = content.impact.items;
        },
        career: () => content.biography.career.splice(idx, 1),
        callout: () => {
          content.biography.callouts.splice(idx, 1);
          content.biography.recognition = content.biography.callouts;
        },
        school: () => content.education.schools.splice(idx, 1),
        gitProject: () => content.aiJourney.gitProjects.splice(idx, 1),
        featuredBuild: () => content.aiJourney.featuredBuilds.splice(idx, 1),
        labItem: () => content.aiLab.items.splice(idx, 1),
        speaking: () => content.speaking.items.splice(idx, 1),
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
