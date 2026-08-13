// Shared behavior across all pages: mobile nav, active link, reveal-on-scroll, themes

const THEME_KEY = "ishita-theme";
const THEMES = [
  { id: "slate", label: "Slate" },
  { id: "ink", label: "Ink" },
  { id: "copper", label: "Copper" },
  { id: "forest", label: "Forest" },
];

function applyTheme(themeId) {
  const id = THEMES.some(t => t.id === themeId) ? themeId : "slate";
  if (id === "slate") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", id);
  try { localStorage.setItem(THEME_KEY, id); } catch (_) {}
  document.querySelectorAll(".theme-switcher button").forEach(btn => {
    btn.setAttribute("aria-pressed", btn.dataset.theme === id ? "true" : "false");
  });
}

function injectThemeSwitcher() {
  const footer = document.querySelector(".site-footer .wrap") || document.querySelector(".site-footer");
  if (!footer || footer.querySelector(".theme-switcher")) return;

  const switcher = document.createElement("div");
  switcher.className = "theme-switcher";
  switcher.setAttribute("role", "group");
  switcher.setAttribute("aria-label", "Color palette");
  switcher.innerHTML = `
    <span class="theme-label">Palette</span>
    ${THEMES.map(t => `<button type="button" data-theme="${t.id}">${t.label}</button>`).join("")}
  `;
  switcher.addEventListener("click", e => {
    const btn = e.target.closest("button[data-theme]");
    if (!btn) return;
    applyTheme(btn.dataset.theme);
  });
  footer.appendChild(switcher);
}

(function earlyTheme() {
  try {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved && saved !== "slate") document.documentElement.setAttribute("data-theme", saved);
  } catch (_) {}
})();

document.addEventListener("DOMContentLoaded", () => {
  // Mobile nav toggle
  const toggle = document.querySelector(".nav-toggle");
  const links = document.querySelector(".nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", () => links.classList.toggle("open"));
    links.querySelectorAll("a").forEach(a =>
      a.addEventListener("click", () => links.classList.remove("open"))
    );
  }

  // More dropdown
  document.querySelectorAll(".nav-more").forEach(more => {
    const btn = more.querySelector(".nav-more-btn");
    if (!btn) return;
    btn.addEventListener("click", e => {
      e.stopPropagation();
      const open = more.classList.toggle("open");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  });
  document.addEventListener("click", () => {
    document.querySelectorAll(".nav-more.open").forEach(m => {
      m.classList.remove("open");
      m.querySelector(".nav-more-btn")?.setAttribute("aria-expanded", "false");
    });
  });

  // Highlight active nav link based on current page
  const current = location.pathname.split("/").pop() || "index.html";
  const morePages = new Set(["books.html", "art.html", "hiking.html", "education.html"]);
  document.querySelectorAll(".nav-links a").forEach(a => {
    const href = a.getAttribute("href");
    if (href === current || (current === "" && href === "index.html")) {
      a.classList.add("active");
    }
  });
  if (morePages.has(current)) {
    document.querySelector(".nav-more-btn")?.classList.add("active");
  }

  // Reveal-on-scroll
  const revealEls = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && revealEls.length) {
    const io = new IntersectionObserver(
      entries => {
        entries.forEach(e => {
          if (e.isIntersecting) {
            e.target.classList.add("in");
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    revealEls.forEach(el => io.observe(el));
  } else {
    revealEls.forEach(el => el.classList.add("in"));
  }

  injectThemeSwitcher();
  try { applyTheme(localStorage.getItem(THEME_KEY) || "slate"); } catch (_) { applyTheme("slate"); }
});
