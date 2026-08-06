#!/usr/bin/env python3
"""Personal site server: static files, content API, uploads, email-gated admin."""

from __future__ import annotations

import cgi
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import time
import urllib.parse
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT_PATH = ROOT / "data" / "content.json"
UPLOAD_ROOT = ROOT / "images"
DOCS_ROOT = ROOT / "uploads"
ALLOWED_FOLDERS = {"hero", "books", "art", "hiking", "pillars", "roles", "projects"}
ALLOWED_EXT = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
    ".pdf", ".ppt", ".pptx", ".key",
    ".doc", ".docx", ".txt", ".rtf",
    ".xls", ".xlsx", ".csv",
    ".zip",
}
PORT = int(os.environ.get("PORT", "8080"))
HOST = os.environ.get("HOST", "0.0.0.0")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "imajumd1@gmail.com").strip().lower()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "local-dev-only")
SESSION_DAYS = 14
COOKIE_NAME = "ishita_admin"
SECRET_PATH = ROOT / "data" / ".secret_key"


def load_secret_key() -> bytes:
    env = os.environ.get("SECRET_KEY", "").strip()
    if env:
        return env.encode()
    SECRET_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SECRET_PATH.exists():
        raw = SECRET_PATH.read_bytes().strip()
        if raw:
            return raw
    key = secrets.token_hex(32).encode()
    SECRET_PATH.write_bytes(key)
    return key


SECRET_KEY = load_secret_key()


def safe_filename(name: str) -> str:
    name = Path(name).name
    name = re.sub(r"[^\w.\-]+", "-", name, flags=re.UNICODE).strip("-.")
    return name or "upload"


def sign_session(email: str, exp: int) -> str:
    payload = f"{email}|{exp}"
    sig = hmac.new(SECRET_KEY, payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{sig}"


def verify_session(token: str | None) -> str | None:
    if not token:
        return None
    parts = token.split("|")
    if len(parts) != 3:
        return None
    email, exp_s, sig = parts
    try:
        exp = int(exp_s)
    except ValueError:
        return None
    if exp < int(time.time()):
        return None
    expected = hmac.new(SECRET_KEY, f"{email}|{exp}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    if email.strip().lower() != ADMIN_EMAIL:
        return None
    return email


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _cookies(self) -> SimpleCookie:
        raw = self.headers.get("Cookie", "")
        c = SimpleCookie()
        if raw:
            c.load(raw)
        return c

    def _session_email(self) -> str | None:
        c = self._cookies()
        morsel = c.get(COOKIE_NAME)
        return verify_session(morsel.value if morsel else None)

    def _is_admin(self) -> bool:
        return self._session_email() is not None

    def _require_admin(self) -> bool:
        if self._is_admin():
            return True
        self._send_json({"ok": False, "error": "Unauthorized"}, 401)
        return False

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, PUT, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/session":
            email = self._session_email()
            return self._send_json({
                "authenticated": bool(email),
                "email": email or "",
            })

        if path == "/api/content":
            return self._send_json(self._read_content())

        # Gate admin UI
        if path in ("/admin.html", "/admin", "/admin/", "/Admin", "/Admin/", "/edit", "/edit/", "/editor"):
            if not self._is_admin():
                self.send_response(302)
                self.send_header("Location", "/login.html?next=admin.html")
                self.end_headers()
                return
            if path != "/admin.html":
                self.send_response(302)
                self.send_header("Location", "/admin.html")
                self.end_headers()
                return

        # Common typo: trailing punctuation on admin URL
        if path.rstrip(".") in ("/admin.html", "/admin") and path != path.rstrip("."):
            self.send_response(302)
            self.send_header("Location", "/admin.html")
            self.end_headers()
            return

        return super().do_GET()

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/content":
            if not self._require_admin():
                return
            return self._save_content()
        self.send_error(404, "Not found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/login":
            return self._login()
        if parsed.path == "/api/logout":
            return self._logout()
        if parsed.path == "/api/upload":
            if not self._require_admin():
                return
            return self._upload()
        self.send_error(404, "Not found")

    def _login(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return self._send_json({"ok": False, "error": "Invalid JSON"}, 400)

        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", ""))

        if email != ADMIN_EMAIL or not hmac.compare_digest(password, ADMIN_PASSWORD):
            # Constant-ish delay
            time.sleep(0.4)
            return self._send_json({"ok": False, "error": "Access denied for that email."}, 403)

        exp = int(time.time()) + SESSION_DAYS * 24 * 3600
        token = sign_session(email, exp)
        body = json.dumps({"ok": True, "email": email}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        secure = " Secure;" if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("FORCE_SECURE_COOKIE") else ""
        self.send_header(
            "Set-Cookie",
            f"{COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_DAYS * 86400};{secure}",
        )
        self.end_headers()
        self.wfile.write(body)

    def _logout(self):
        body = json.dumps({"ok": True}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header(
            "Set-Cookie",
            f"{COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0",
        )
        self.end_headers()
        self.wfile.write(body)

    def _read_content(self):
        with CONTENT_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _save_content(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return self._send_json({"ok": False, "error": "Invalid JSON"}, 400)

        CONTENT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CONTENT_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        return self._send_json({"ok": True})

    def _upload(self):
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            return self._send_json({"ok": False, "error": "Expected multipart form"}, 400)

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": content_type,
            },
        )

        folder = (form.getvalue("folder") or "hero").strip()
        if folder not in ALLOWED_FOLDERS:
            return self._send_json({"ok": False, "error": "Invalid folder"}, 400)

        file_item = form["file"] if "file" in form else None
        if file_item is None or not getattr(file_item, "filename", None):
            return self._send_json({"ok": False, "error": "No file uploaded"}, 400)

        filename = safe_filename(file_item.filename)
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXT:
            return self._send_json(
                {"ok": False, "error": f"File type not allowed: {ext or '(none)'}"},
                400,
            )

        # Docs/slides for roles live under uploads/; images under images/
        if folder == "roles":
            dest_dir = DOCS_ROOT / "roles"
            url_prefix = "uploads/roles"
        else:
            dest_dir = UPLOAD_ROOT / folder
            url_prefix = f"images/{folder}"

        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / filename

        if dest.exists():
            stem = dest.stem
            n = 2
            while True:
                candidate = dest_dir / f"{stem}-{n}{ext}"
                if not candidate.exists():
                    dest = candidate
                    break
                n += 1

        dest.write_bytes(file_item.file.read())
        rel = f"{url_prefix}/{dest.name}"
        return self._send_json({
            "ok": True,
            "path": rel,
            "name": dest.name,
            "type": ext.lstrip("."),
        })

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main():
    os.chdir(ROOT)
    CONTENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    (DOCS_ROOT / "roles").mkdir(parents=True, exist_ok=True)
    if not CONTENT_PATH.exists():
        CONTENT_PATH.write_text("{}\n", encoding="utf-8")

    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Site running at http://127.0.0.1:{PORT}/")
    print(f"Admin login:  http://127.0.0.1:{PORT}/login.html")
    print(f"Admin email:  {ADMIN_EMAIL}")
    if ADMIN_PASSWORD == "local-dev-only":
        print("Admin password: local-dev-only  (set ADMIN_PASSWORD on Railway)")
    else:
        print("Admin password: (from ADMIN_PASSWORD env)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
