/* Lightweight rich-text editor for admin fields */

function rteEscape(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function plainToHtml(text) {
  const raw = String(text ?? "").trim();
  if (!raw) return "";
  if (/<[a-z][\s\S]*>/i.test(raw)) return raw;
  return raw
    .split(/\n\s*\n/)
    .map(p => `<p>${rteEscape(p).replace(/\n/g, "<br>")}</p>`)
    .join("");
}

function createRte(initialHtml, opts = {}) {
  const minHeight = opts.minHeight || "110px";
  const wrap = document.createElement("div");
  wrap.className = "rte";
  wrap.innerHTML = `
    <div class="rte-toolbar" role="toolbar" aria-label="Formatting">
      <button type="button" data-cmd="bold" title="Bold"><b>B</b></button>
      <button type="button" data-cmd="italic" title="Italic"><i>I</i></button>
      <button type="button" data-cmd="underline" title="Underline"><u>U</u></button>
      <span class="rte-sep"></span>
      <button type="button" data-cmd="insertUnorderedList" title="Bullets">• List</button>
      <button type="button" data-cmd="insertOrderedList" title="Numbered">1. List</button>
      <span class="rte-sep"></span>
      <button type="button" data-cmd="formatBlock" data-value="h3" title="Heading">H</button>
      <button type="button" data-cmd="formatBlock" data-value="p" title="Paragraph">¶</button>
      <button type="button" data-cmd="createLink" title="Link">Link</button>
      <button type="button" data-cmd="removeFormat" title="Clear formatting">Clear</button>
    </div>
    <div class="rte-editor" contenteditable="true" style="min-height:${minHeight}"></div>
  `;
  const editor = wrap.querySelector(".rte-editor");
  editor.innerHTML = plainToHtml(initialHtml);

  wrap.querySelectorAll(".rte-toolbar button").forEach(btn => {
    btn.addEventListener("mousedown", e => e.preventDefault());
    btn.addEventListener("click", () => {
      editor.focus();
      const cmd = btn.dataset.cmd;
      if (cmd === "createLink") {
        const url = prompt("Link URL", "https://");
        if (url) document.execCommand("createLink", false, url);
        return;
      }
      if (cmd === "formatBlock") {
        document.execCommand("formatBlock", false, btn.dataset.value || "p");
        return;
      }
      document.execCommand(cmd, false, null);
    });
  });

  return wrap;
}

function rteField(label, key, html, opts = {}) {
  const field = document.createElement("div");
  field.className = "field";
  const lab = document.createElement("label");
  lab.textContent = label;
  field.appendChild(lab);
  const rte = createRte(html, opts);
  rte.dataset.rteKey = key;
  field.appendChild(rte);
  return field;
}

function getRteHtml(root, key) {
  const editor = root.querySelector(`.rte[data-rte-key="${key}"] .rte-editor`);
  if (!editor) return "";
  const html = editor.innerHTML.trim();
  if (!html || html === "<br>" || html === "<p><br></p>") return "";
  return html;
}

function setStaticRte(containerId, html, opts = {}) {
  const host = document.getElementById(containerId);
  if (!host) return;
  host.innerHTML = "";
  const rte = createRte(html, opts);
  rte.dataset.rteKey = containerId;
  host.appendChild(rte);
}

function getStaticRte(containerId) {
  return getRteHtml(document.getElementById(containerId) || document, containerId);
}
