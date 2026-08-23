"""Roma's own HTTP server: its JSON API and its own static UI, one process.

Standard library only. It serves nothing outside Roma's own ``static``
directory, so it has no relationship to any other site on the machine.
"""

from __future__ import annotations

import json
import mimetypes
import posixpath
import sys
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import VERSION, airports
from .config import Config
from .conversation import Conversation
from .engine import Engine

MAX_BODY_BYTES = 64 * 1024

_TEXT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".json": "application/json; charset=utf-8",
    ".webmanifest": "application/manifest+json",
    ".ico": "image/x-icon",
}


class RomaHandler(BaseHTTPRequestHandler):
    server_version = f"Roma/{VERSION}"
    protocol_version = "HTTP/1.1"

    # injected by serve()
    engine: Engine
    conversation: Conversation
    config: Config

    # -- plumbing -----------------------------------------------------------
    def log_message(self, fmt: str, *args) -> None:  # quieter, timestamped
        stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        sys.stderr.write(f"[roma {stamp}] {self.address_string()} {fmt % args}\n")

    def _send(self, status: int, body: bytes, content_type: str, extra: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8", {"Cache-Control": "no-store"})

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        if length > MAX_BODY_BYTES:
            raise ValueError("request body too large")
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"body is not valid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("body must be a JSON object")
        return payload

    # -- routing ------------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        try:
            parsed = urlparse(self.path)
            route = parsed.path.rstrip("/") or "/"
            query = parse_qs(parsed.query)

            if route == "/api/health":
                return self._json(200, {"ok": True, "agent": "Roma", "version": VERSION})
            if route == "/api/meta":
                return self._json(200, self.engine.meta())
            if route == "/api/airports":
                term = (query.get("q") or [""])[0]
                limit = min(20, max(1, int((query.get("limit") or ["8"])[0] or 8)))
                return self._json(
                    200, {"ok": True, "query": term, "results": airports.search(term, limit)}
                )
            if route.startswith("/api/"):
                return self._json(404, {"ok": False, "error": f"No such endpoint: {route}"})
            return self._serve_static(parsed.path)
        except Exception:
            self._fail()

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def do_POST(self) -> None:  # noqa: N802
        try:
            route = urlparse(self.path).path.rstrip("/") or "/"
            try:
                payload = self._read_json()
            except ValueError as exc:
                return self._json(400, {"ok": False, "error": str(exc)})

            if route == "/api/search":
                return self._json(200, self.engine.search(payload))
            if route == "/api/chat":
                session_id = str(payload.get("session_id") or "").strip()
                if not session_id:
                    session_id = self.conversation.new_session_id()
                message = str(payload.get("message") or "")
                return self._json(200, self.conversation.handle(session_id, message))
            if route == "/api/session":
                return self._json(200, {"ok": True, "session_id": self.conversation.new_session_id()})
            return self._json(404, {"ok": False, "error": f"No such endpoint: {route}"})
        except Exception:
            self._fail()

    def _fail(self) -> None:
        detail = traceback.format_exc()
        sys.stderr.write(detail)
        try:
            self._json(500, {"ok": False, "error": "Roma hit an internal error. See server output."})
        except Exception:
            pass

    # -- static -------------------------------------------------------------
    def _serve_static(self, url_path: str) -> None:
        root = self.config.static_dir.resolve()
        relative = unquote(url_path)
        if relative in ("", "/"):
            relative = "/index.html"
        clean = posixpath.normpath(relative).lstrip("/")
        target = (root / clean).resolve()
        if not str(target).startswith(str(root)) or not target.is_file():
            body = b"Not found. Roma serves only its own interface."
            return self._send(404, body, "text/plain; charset=utf-8")

        suffix = target.suffix.lower()
        content_type = _TEXT_TYPES.get(suffix) or mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        cache = "no-store" if suffix in {".html", ".css", ".js"} else "public, max-age=3600"
        self._send(200, target.read_bytes(), content_type, {"Cache-Control": cache})


def build_server(config: Config) -> ThreadingHTTPServer:
    engine = Engine(config)
    handler = type(
        "BoundRomaHandler",
        (RomaHandler,),
        {"engine": engine, "conversation": Conversation(engine), "config": config},
    )
    httpd = ThreadingHTTPServer((config.host, config.port), handler)
    httpd.daemon_threads = True
    return httpd


def serve(config: Config) -> None:
    httpd = build_server(config)
    url = f"http://{config.host}:{config.port}/"
    described = Engine(config).config.describe()
    print(f"Roma is listening on {url}", flush=True)
    print(
        f"  fares: {described['fare_provider']}   language: {described['language_mode']}   "
        f"history: {config.db_path}",
        flush=True,
    )
    print("  every fare Roma shows is simulated; press Ctrl+C to stop", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nRoma stopped.", flush=True)
    finally:
        httpd.server_close()
