"""Stdlib HTTP demo. No passwords, no API keys, no outbound calls."""

from __future__ import annotations

import json
import posixpath
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from demo.night_desk import ingest
from demo.store import DeskStore

HOST = "127.0.0.1"
PORT = 8765
STATIC = Path(__file__).resolve().parent / "static"
ALLOWED_USERS = ("demo@atlas.local", "other@atlas.local")
COOKIE_NAME = "desk_user"
DEFAULT_USER = ALLOWED_USERS[0]
STORE = DeskStore()


def _json_bytes(payload: object, status: int = 200) -> tuple[int, bytes, str]:
    body = json.dumps(payload, indent=2).encode("utf-8")
    return status, body, "application/json; charset=utf-8"


class Handler(BaseHTTPRequestHandler):
    server_version = "AIDeskDemo/0.1"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} {fmt % args}")

    def _user(self) -> str:
        raw = self.headers.get("Cookie", "")
        jar = cookies.SimpleCookie()
        try:
            jar.load(raw)
        except cookies.CookieError:
            return DEFAULT_USER
        if COOKIE_NAME in jar:
            value = jar[COOKIE_NAME].value
            if value in ALLOWED_USERS:
                return value
        return DEFAULT_USER

    def _send(self, status: int, body: bytes, content_type: str, extra: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if extra:
            for key, value in extra.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON object required")
        return data

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        user = self._user()

        if path == "/api/session":
            status, body, ctype = _json_bytes(
                {
                    "user": user,
                    "users": list(ALLOWED_USERS),
                    "counts": STORE.counts(user),
                    "isolation": {
                        u: STORE.counts(u) for u in ALLOWED_USERS
                    },
                }
            )
            self._send(status, body, ctype)
            return

        if path == "/api/desk":
            status, body, ctype = _json_bytes({"user": user, "desk": STORE.desk(user)})
            self._send(status, body, ctype)
            return

        if path in {"/", "/index.html"}:
            self._static("index.html")
            return

        if path.startswith("/static/"):
            self._static(path[len("/static/") :])
            return

        # Serve CSS/JS from / as well so index can use relative paths.
        name = posixpath.basename(path)
        if name in {"app.js", "style.css"}:
            self._static(name)
            return

        self._send(404, b'{"error":"not found"}\n', "application/json; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        user = self._user()

        if path == "/api/login":
            try:
                data = self._read_json()
            except (ValueError, json.JSONDecodeError) as exc:
                status, body, ctype = _json_bytes({"error": str(exc)}, 400)
                self._send(status, body, ctype)
                return
            nxt = str(data.get("user") or "")
            if nxt not in ALLOWED_USERS:
                status, body, ctype = _json_bytes({"error": "unknown user"}, 400)
                self._send(status, body, ctype)
                return
            crumb = cookies.SimpleCookie()
            crumb[COOKIE_NAME] = nxt
            crumb[COOKIE_NAME]["path"] = "/"
            crumb[COOKIE_NAME]["httponly"] = True
            crumb[COOKIE_NAME]["samesite"] = "Lax"
            status, body, ctype = _json_bytes({"user": nxt, "desk": STORE.desk(nxt)})
            self._send(status, body, ctype, {"Set-Cookie": crumb.output(header="").strip()})
            return

        if path == "/api/drop":
            try:
                data = self._read_json()
                job_text = str(data.get("text") or "")
                artifacts = ingest(job_text, target_user=user)
                desk = STORE.write_artifacts(
                    user, artifacts["mail"], artifacts["file"], artifacts["calendar"]
                )
            except (ValueError, json.JSONDecodeError) as exc:
                status, body, ctype = _json_bytes({"error": str(exc)}, 400)
                self._send(status, body, ctype)
                return
            status, body, ctype = _json_bytes(
                {"user": user, "artifacts": artifacts, "desk": desk}
            )
            self._send(status, body, ctype)
            return

        # Allow query-string login from the static form as a fallback.
        if path == "/login":
            nxt = (parse_qs(parsed.query).get("user") or [""])[0]
            if nxt not in ALLOWED_USERS:
                self._send(400, b'{"error":"unknown user"}\n', "application/json; charset=utf-8")
                return
            crumb = cookies.SimpleCookie()
            crumb[COOKIE_NAME] = nxt
            crumb[COOKIE_NAME]["path"] = "/"
            self._send(204, b"", "text/plain", {"Set-Cookie": crumb.output(header="").strip(), "Location": "/"})
            return

        self._send(404, b'{"error":"not found"}\n', "application/json; charset=utf-8")

    def _static(self, name: str) -> None:
        safe = posixpath.normpath(name).lstrip("/")
        if safe.startswith(".."):
            self._send(404, b"not found\n", "text/plain; charset=utf-8")
            return
        path = (STATIC / safe).resolve()
        if not str(path).startswith(str(STATIC.resolve())) or not path.is_file():
            self._send(404, b"not found\n", "text/plain; charset=utf-8")
            return
        data = path.read_bytes()
        types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
        }
        self._send(200, data, types.get(path.suffix, "application/octet-stream"))


def main() -> None:
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"AI Desk demo http://{HOST}:{PORT}", flush=True)
    print(f"Logins (no passwords): {', '.join(ALLOWED_USERS)}", flush=True)
    print("Ctrl-C to stop.", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
        httpd.server_close()


if __name__ == "__main__":
    main()
