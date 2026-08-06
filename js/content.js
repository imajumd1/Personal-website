// Shared content loader for public pages
async function loadContent() {
  const res = await fetch("data/content.json", { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load content");
  return res.json();
}

async function getSession() {
  try {
    const res = await fetch("/api/session", { cache: "no-store", credentials: "same-origin" });
    if (!res.ok) return { authenticated: false };
    return res.json();
  } catch {
    return { authenticated: false };
  }
}

function applySiteChrome(content, session) {
  const brand = content.site?.brand || "Ishita";
  const email = content.site?.email || "";

  document.querySelectorAll(".brand").forEach(el => { el.textContent = brand; });
  document.querySelectorAll(".brand-text").forEach(el => { el.textContent = brand; });

  if (document.title.includes("—") || document.title.includes("–") || document.title.includes(" - ")) {
    document.title = document.title.replace(/^.*?(?=\s*[—–-]\s*)/, brand);
  }

  document.querySelectorAll(".site-footer a[href^='mailto:']").forEach(el => {
    if (email) {
      el.href = `mailto:${email}`;
      el.textContent = email;
    }
  });

  // Remove any public edit links
  document.querySelectorAll(".edit-link").forEach(el => el.remove());

  injectAdminNav(session);
}

function injectAdminNav(session) {
  const nav = document.querySelector(".site-nav .wrap");
  if (!nav) return;

  let slot = document.getElementById("admin-access-slot");
  if (!slot) {
    slot = document.createElement("div");
    slot.id = "admin-access-slot";
    slot.className = "admin-access-slot";
    // Place beside the brand so it stays visible on every page width
    const brand = nav.querySelector(".brand");
    if (brand && brand.nextSibling) nav.insertBefore(slot, brand.nextSibling);
    else nav.appendChild(slot);
  }

  // Floating edit button — easy to spot on any page
  let fab = document.getElementById("admin-fab");
  if (!fab) {
    fab = document.createElement("a");
    fab.id = "admin-fab";
    fab.className = "admin-fab";
    fab.href = "admin.html";
    document.body.appendChild(fab);
  }

  if (session?.authenticated) {
    slot.innerHTML = `
      <a class="btn btn-primary admin-access-btn" href="admin.html">Admin</a>
      <button type="button" class="btn btn-ghost btn-small" id="admin-logout" title="Log out">Log out</button>
    `;
    fab.hidden = false;
    fab.textContent = "Edit site";
    fab.setAttribute("aria-label", "Open admin editor");
    document.getElementById("admin-logout")?.addEventListener("click", async () => {
      await fetch("/api/logout", { method: "POST", credentials: "same-origin" });
      location.reload();
    });
  } else {
    slot.innerHTML = "";
    fab.hidden = true;
  }
}

async function bootChrome(content) {
  const session = await getSession();
  applySiteChrome(content, session);
  return session;
}

/** Apply editable page-hero eyebrow / title / lede from content. */
function applyPageHero(page) {
  if (!page) return;
  const eyebrow = document.querySelector(".page-hero .eyebrow");
  const title = document.querySelector(".page-hero h1");
  const lede = document.querySelector(".page-hero .lede");
  if (eyebrow && page.eyebrow != null && page.eyebrow !== "") {
    eyebrow.textContent = page.eyebrow;
  }
  if (title && page.title != null && page.title !== "") {
    title.textContent = page.title;
  }
  if (lede && page.lede != null) {
    lede.classList.add("rich-text");
    lede.innerHTML = richHtml(page.lede);
  }
}

/** Normalize pages that used to be bare arrays into { items: [...] }. */
function pageItems(section) {
  if (Array.isArray(section)) return section;
  return section?.items || [];
}

function escapeHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function htmlToPlainText(html) {
  const tmp = document.createElement("div");
  tmp.innerHTML = String(html ?? "");
  return (tmp.textContent || "").replace(/\s+/g, " ").trim();
}

function sanitizeHtml(html) {
  const raw = String(html ?? "");
  if (!raw) return "";
  // Already plain text
  if (!/<[a-z][\s\S]*>/i.test(raw)) {
    return `<p>${escapeHtml(raw)}</p>`;
  }
  const template = document.createElement("template");
  template.innerHTML = raw;
  const allowed = new Set(["P", "BR", "STRONG", "B", "EM", "I", "U", "UL", "OL", "LI", "A", "H3", "H4", "SPAN"]);
  const walk = node => {
    [...node.children].forEach(child => {
      if (!allowed.has(child.tagName)) {
        const parent = child.parentNode;
        while (child.firstChild) parent.insertBefore(child.firstChild, child);
        parent.removeChild(child);
        return;
      }
      [...child.attributes].forEach(attr => {
        const name = attr.name.toLowerCase();
        if (child.tagName === "A" && name === "href") {
          const href = child.getAttribute("href") || "";
          if (!/^(https?:|mailto:|\/|#)/i.test(href)) child.removeAttribute("href");
          child.setAttribute("rel", "noopener");
          child.setAttribute("target", "_blank");
          return;
        }
        child.removeAttribute(attr.name);
      });
      walk(child);
    });
  };
  walk(template.content);
  return template.innerHTML.trim();
}

function richHtml(value) {
  if (Array.isArray(value)) {
    return sanitizeHtml(value.map(p => `<p>${escapeHtml(p)}</p>`).join(""));
  }
  return sanitizeHtml(value);
}

function truncateWords(text, maxWords = 55) {
  const words = String(text || "").trim().split(/\s+/).filter(Boolean);
  if (words.length <= maxWords) {
    return { preview: words.join(" "), full: words.join(" "), truncated: false };
  }
  return {
    preview: words.slice(0, maxWords).join(" ") + "…",
    full: words.join(" "),
    truncated: true
  };
}

function truncateRich(html, maxWords = 24) {
  const fullHtml = richHtml(html);
  const plain = htmlToPlainText(fullHtml);
  const cut = truncateWords(plain, maxWords);
  if (!cut.truncated) {
    return { previewHtml: fullHtml, fullHtml, truncated: false };
  }
  return {
    previewHtml: `<p>${escapeHtml(cut.preview)}</p>`,
    fullHtml,
    truncated: true
  };
}

function fileIconLabel(type) {
  const t = (type || "").toLowerCase();
  if (["pdf"].includes(t)) return "PDF";
  if (["ppt", "pptx", "key"].includes(t)) return "Slides";
  if (["doc", "docx", "rtf", "txt"].includes(t)) return "Doc";
  if (["xls", "xlsx", "csv"].includes(t)) return "Sheet";
  if (["jpg", "jpeg", "png", "gif", "webp", "svg"].includes(t)) return "Image";
  return (t || "File").toUpperCase();
}
